#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from typing import Any

from timelog import integrations as cli_config
from timelog import paths, updater
from timelog.browser import auth as webview_auth
from timelog.config import APP_VERSION, DEFAULT_PORT
from timelog.server.modules import calendar as ombiel_calendar
from timelog.server.modules import client as timelog_client
from timelog.server.modules import qmplus as qmplus_client
from timelog.server.modules.schemas import AuthRequired

HERE = str(paths.ROOT)
UI_FILE = str(paths.BUNDLE_DIR / "timelog" / "desktop" / "ui" / "index.html")
ICON_FILE = str(paths.BUNDLE_DIR / "timelog" / "desktop" / "ui" / "icons" / "timelog.ico")
MCP_SERVER = str(paths.SERVER_SCRIPT)
TOKENS_FILE = str(paths.TOKENS_FILE)

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


def _err(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


class Api:
    def __init__(self) -> None:
        self._window: Any = None
        self._mcp_proc: subprocess.Popen[bytes] | None = None
        self._mcp_port: int = DEFAULT_PORT
        self._keepalive_stop: threading.Event | None = None
        self._login_running: dict[str, bool] = {
            "session": False,
            "ombiel": False,
            "qmplus": False,
        }
        self._ui_ready: bool = False

    def _start_login(self, service: str, name: str) -> dict[str, Any]:
        if self._login_running.get(service):
            return {"ok": True, "message": f"{name} already running"}

        self._login_running[service] = True

        def _done(_ok: bool) -> None:
            self._login_running[service] = False

        try:
            webview_auth.open_login_window(service, on_done=_done)
            return {"ok": True, "message": "sign-in window opened"}
        except Exception as exc:
            self._login_running[service] = False
            return {"ok": False, "error": _err(exc)}

    def ui_ready(self) -> dict[str, bool]:
        self._ui_ready = True
        return {"ok": True}

    def minimize(self) -> dict[str, bool]:
        if self._window:
            self._window.minimize()
        return {"ok": True}

    def close(self) -> dict[str, bool]:
        self.stop_keepalive()
        self.stop_mcp()
        if self._window:
            self._window.destroy()
        return {"ok": True}

    def start_keepalive(self) -> dict[str, Any]:
        if self._keepalive_stop and not self._keepalive_stop.is_set():
            return {"ok": True, "running": True, "message": "already running"}

        stop = threading.Event()
        self._keepalive_stop = stop

        def _loop() -> None:
            while not stop.wait(170):
                try:
                    timelog_client.Auth(TOKENS_FILE).ensure_valid()
                except Exception:
                    pass

        threading.Thread(target=_loop, daemon=True).start()
        return {"ok": True, "running": True}

    def stop_keepalive(self) -> dict[str, Any]:
        if self._keepalive_stop:
            self._keepalive_stop.set()
            self._keepalive_stop = None
        return {"ok": True, "running": False}

    def start_login(self) -> dict[str, Any]:
        return self._start_login("session", "login")

    def start_calendar_login(self) -> dict[str, Any]:
        return self._start_login("ombiel", "calendar login")

    def start_qmplus_login(self) -> dict[str, Any]:
        return self._start_login("qmplus", "qmplus login")

    def bootstrap(self) -> dict[str, Any]:
        # Intentionally offline: never block window startup on a token refresh.
        return {
            "token": timelog_client.token_state(TOKENS_FILE),
            "timelog_login_running": self._login_running["session"],
            "targets": cli_config.targets(),
            "mcp": self.mcp_state(),
            "calendar": self.calendar_state(),
            "qmplus": self.qmplus_state(),
            "profile": None,
            "types": [],
            "error": None,
        }

    def calendar_state(self) -> dict[str, Any]:
        try:
            state = ombiel_calendar.token_state()
        except Exception as exc:
            state = {"connected": False, "error": _err(exc)}

        state["login_running"] = self._login_running["ombiel"]
        state["tokens_file"] = str(paths.OMBIEL_TOKENS_FILE)
        return state

    def qmplus_state(self) -> dict[str, Any]:
        try:
            state = qmplus_client.session_state()
        except Exception as exc:
            state = {"connected": False, "error": _err(exc)}

        state["login_running"] = self._login_running["qmplus"]
        state["tokens_file"] = str(paths.QMPLUS_TOKENS_FILE)
        return state

    def qmplus_check(self) -> dict[str, Any]:
        try:
            courses = qmplus_client.QmplusClient().courses()
            return {"ok": True, "valid": True, "count": len(courses)}
        except AuthRequired as exc:
            return {"ok": False, "authRequired": True, "error": str(exc), "valid": False}
        except Exception as exc:
            return {"ok": False, "error": _err(exc), "valid": False}

    def mcp_state(self) -> dict[str, Any]:
        running = bool(self._mcp_proc and self._mcp_proc.poll() is None)
        if not running and _port_open(self._mcp_port):
            # A server from a previous run is still bound to the port.
            return {
                "running": True,
                "external": True,
                "port": self._mcp_port,
                "url": f"http://127.0.0.1:{self._mcp_port}/mcp",
            }

        return {
            "running": running,
            "external": False,
            "port": self._mcp_port,
            "pid": self._mcp_proc.pid if running else None,
            "url": f"http://127.0.0.1:{self._mcp_port}/mcp" if running else None,
        }

    def start_mcp(self, port: int = DEFAULT_PORT) -> dict[str, Any]:
        try:
            port = int(port or DEFAULT_PORT)
        except Exception:
            port = DEFAULT_PORT

        if self._mcp_proc and self._mcp_proc.poll() is None:
            return {"ok": True, "message": "already running", **self.mcp_state()}

        if _port_open(port):
            self._mcp_port = port
            return {
                "ok": True,
                "message": "a server is already listening on this port",
                "external": True,
                **self.mcp_state(),
            }

        try:
            self._mcp_port = port
            paths.ensure_data_dir()
            mcp_log = open(paths.DATA_DIR / "mcp.log", "ab", buffering=0)
            try:
                self._mcp_proc = subprocess.Popen(
                    paths.mcp_command("--transport", "http", "--port", str(port)),
                    cwd=HERE,
                    stdin=subprocess.DEVNULL,
                    stdout=mcp_log,
                    stderr=subprocess.STDOUT,
                    creationflags=CREATE_NO_WINDOW,
                )
            finally:
                mcp_log.close()

            deadline = time.time() + 8
            while time.time() < deadline:
                if self._mcp_proc.poll() is not None:
                    return {
                        "ok": False,
                        "error": "server exited immediately (see console)",
                    }
                if _port_open(port):
                    break
                time.sleep(0.2)

            return {"ok": True, **self.mcp_state()}
        except Exception as exc:
            return {"ok": False, "error": _err(exc)}

    def stop_mcp(self) -> dict[str, Any]:
        try:
            if self._mcp_proc and self._mcp_proc.poll() is None:
                self._mcp_proc.terminate()
                try:
                    self._mcp_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._mcp_proc.kill()
            self._mcp_proc = None
            return {"ok": True, **self.mcp_state()}
        except Exception as exc:
            return {"ok": False, "error": _err(exc)}

    def targets(self) -> dict[str, Any]:
        return {"ok": True, "targets": cli_config.targets()}

    def install(self, targets: list[str], transport: str = "stdio") -> dict[str, Any]:
        results = cli_config.install(targets or [], transport)
        return {"ok": all(r.get("ok") for r in results), "results": results}

    def remove_servers(self, targets: list[str]) -> dict[str, Any]:
        return {"ok": True, "results": cli_config.remove(targets or [])}

    def mcp_prompt(self) -> dict[str, Any]:
        cmd = paths.mcp_command()
        targets = cli_config.targets()
        locations = "\n".join(f"- {t['name']}: {t['path']}" for t in targets)
        snippet = json.dumps(
            {
                "mcpServers": {
                    "timelog": {
                        "command": cmd[0],
                        "args": cmd[1:],
                    }
                }
            },
            indent=2,
        )
        tools = (
            "auth_status, get_profile, list_activity_types, list_entries, add_entry, "
            "delete_entry, get_totals, get_otj_guide, check_entry, "
            "calendar_status, calendar_list, calendar_events, calendar_upcoming, "
            "qmplus_status, qmplus_courses, qmplus_course_contents, "
            "qmplus_search, qmplus_fetch, qmplus_current_lecture, ping"
        )
        prompt = (
            "Please add the following local MCP server to this AI client.\n\n"
            "Server name: timelog\n"
            "Transport: stdio\n"
            f"Command: {cmd[0]}\n"
            f"Args: {json.dumps(cmd[1:])}\n"
            f"Working directory (if the client supports one): {HERE}\n\n"
            "Steps:\n"
            "1. Find this client's MCP configuration file (see candidate paths below).\n"
            "2. Back it up before editing.\n"
            "3. Merge an entry named \"timelog\" with the command/args above. "
            "Preserve every existing server and setting.\n"
            "4. Restart or reload the client so it picks up the server.\n"
            "5. Tell me the exact file changed and show the added snippet.\n\n"
            "Config snippet (stdio):\n"
            f"{snippet}\n\n"
            "Candidate config locations on this machine:\n"
            f"{locations}\n\n"
            "If this client only supports remote/HTTP MCP servers, use "
            "http://127.0.0.1:8765/mcp instead; the desktop app must be running "
            "with the local MCP server started.\n\n"
            f"Available tools: {tools}.\n\n"
            "Do not print, copy, or ask for any access tokens. Credentials stay "
            f"in {paths.DATA_DIR} and must not be added to the config."
        )

        return {
            "ok": True,
            "prompt": prompt,
            "command": cmd[0],
            "args": cmd[1:],
            "snippet": snippet,
            "targets": targets,
        }

    def check_update(self) -> dict[str, Any]:
        return updater.check_update()

    def install_update(self, download_url: str) -> dict[str, Any]:
        result = updater.apply_update(download_url)
        if result.get("ok"):
            self.close()
        return result

    def reveal(self, path: str) -> dict[str, Any]:
        try:
            target = path
            if target.lower().endswith((".json", ".toml")):
                target = os.path.dirname(target)
            if not os.path.isdir(target):
                target = str(paths.DATA_DIR)

            if os.name == "nt":
                os.startfile(target)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])

            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": _err(exc)}

    def app_info(self) -> dict[str, Any]:
        return {
            "version": APP_VERSION,
            "frozen": paths.FROZEN,
            "here": HERE,
            "data": str(paths.DATA_DIR),
            "python": sys.executable,
            "tokens": TOKENS_FILE,
            "calendar_tokens": str(paths.OMBIEL_TOKENS_FILE),
            "calendar_profile": str(paths.OMBIEL_PROFILE_DIR),
            "qmplus_tokens": str(paths.QMPLUS_TOKENS_FILE),
            "mcp_server": MCP_SERVER,
            "port": self._mcp_port,
            "platform": sys.platform,
        }

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from typing import Any

from timelog import auth as webview_auth
from timelog import paths
from timelog.config import (
    APP_VERSION,
    AUTH_SERVICES,
    KEEPALIVE_INTERVAL_S,
    MCP_SERVER_NAME,
    MCP_TOOL_NAMES,
)
from timelog.core import http
from timelog.mcp import clients as mcp_clients
from timelog.services import calendar as calendar_svc
from timelog.services import qmplus as qmplus_svc
from timelog.services import timelog as timelog_svc


class Api:
    def __init__(self) -> None:
        self._window: Any = None
        self._keepalive_stop: threading.Event | None = None
        self._login_running: dict[str, bool] = {key: False for key in AUTH_SERVICES}
        self._ui_ready: bool = False

    def ui_ready(self) -> dict[str, bool]:
        self._ui_ready = True
        return {"ok": True}

    def minimize(self) -> dict[str, bool]:
        if self._window:
            self._window.minimize()
        return {"ok": True}

    def close(self) -> dict[str, bool]:
        self.stop_keepalive()
        if self._window:
            self._window.destroy()
        return {"ok": True}

    def start_keepalive(self) -> dict[str, Any]:
        if self._keepalive_stop and not self._keepalive_stop.is_set():
            return {"ok": True, "running": True, "message": "already running"}

        stop = threading.Event()
        self._keepalive_stop = stop

        def _loop() -> None:
            while not stop.wait(KEEPALIVE_INTERVAL_S):
                try:
                    timelog_svc.Auth().ensure_valid()
                except Exception:
                    pass

        threading.Thread(target=_loop, daemon=True).start()
        return {"ok": True, "running": True}

    def stop_keepalive(self) -> dict[str, Any]:
        if self._keepalive_stop:
            self._keepalive_stop.set()
            self._keepalive_stop = None
        return {"ok": True, "running": False}

    def start_login(self, service: str) -> dict[str, Any]:
        if service not in AUTH_SERVICES:
            return {"ok": False, "error": f"Unknown service: {service}"}
        if self._login_running.get(service):
            return {"ok": True, "message": f"{service} login already running"}

        self._login_running[service] = True

        def _done(_ok: bool) -> None:
            self._login_running[service] = False

        try:
            webview_auth.open_login_window(service, on_done=_done)
            return {"ok": True, "message": "sign-in window opened"}
        except Exception as exc:
            self._login_running[service] = False
            return {"ok": False, "error": http.err_text(exc)}

    def _service_state(self, service: str, fn: Any, fallback_file: str) -> dict[str, Any]:
        try:
            state = fn()
        except Exception as exc:
            state = {"connected": False, "error": http.err_text(exc)}
        state["login_running"] = self._login_running.get(service, False)
        state.setdefault("tokens_file", fallback_file)
        return state

    def timelog_state(self) -> dict[str, Any]:
        return self._service_state("timelog", timelog_svc.token_state, str(paths.TOKENS_FILE))

    def calendar_state(self) -> dict[str, Any]:
        return self._service_state(
            "calendar", calendar_svc.token_state, str(paths.OMBIEL_TOKENS_FILE)
        )

    def qmplus_state(self) -> dict[str, Any]:
        return self._service_state(
            "qmplus", qmplus_svc.session_state, str(paths.QMPLUS_TOKENS_FILE)
        )

    def qmplus_check(self) -> dict[str, Any]:
        try:
            courses = qmplus_svc.QmplusClient().courses()
            return {"ok": True, "valid": True, "count": len(courses)}
        except http.AuthRequired as exc:
            return {"ok": False, "authRequired": True, "error": str(exc), "valid": False}
        except Exception as exc:
            return {"ok": False, "error": http.err_text(exc), "valid": False}

    def bootstrap(self) -> dict[str, Any]:
        # Intentionally offline: never block window startup on a token refresh.
        return {
            "timelog": self.timelog_state(),
            "calendar": self.calendar_state(),
            "qmplus": self.qmplus_state(),
            "targets": mcp_clients.targets(),
        }

    def targets(self) -> dict[str, Any]:
        return {"ok": True, "targets": mcp_clients.targets()}

    def install(self, targets: list[str]) -> dict[str, Any]:
        results = mcp_clients.install(targets or [])
        return {"ok": all(r.get("ok") for r in results), "results": results}

    def remove_servers(self, targets: list[str]) -> dict[str, Any]:
        return {"ok": True, "results": mcp_clients.remove(targets or [])}

    def mcp_prompt(self) -> dict[str, Any]:
        cmd = paths.mcp_command()
        targets = mcp_clients.targets()
        locations = "\n".join(f"- {t['name']}: {t['path']}" for t in targets)
        snippet = json.dumps(
            {"mcpServers": {MCP_SERVER_NAME: {"command": cmd[0], "args": cmd[1:]}}},
            indent=2,
        )
        tools = ", ".join(MCP_TOOL_NAMES)
        prompt = (
            "Please add the following local MCP server to this AI client.\n\n"
            f"Server name: {MCP_SERVER_NAME}\n"
            "Transport: stdio\n"
            f"Command: {cmd[0]}\n"
            f"Args: {json.dumps(cmd[1:])}\n"
            f"Working directory (if the client supports one): {paths.ROOT}\n\n"
            "Steps:\n"
            "1. Find this client's MCP configuration file (see candidate paths below).\n"
            "2. Back it up before editing.\n"
            f'3. Merge an entry named "{MCP_SERVER_NAME}" with the command/args above. '
            "Preserve every existing server and setting.\n"
            "4. Restart or reload the client so it picks up the server.\n"
            "5. Tell me the exact file changed and show the added snippet.\n\n"
            "Config snippet (stdio):\n"
            f"{snippet}\n\n"
            "Candidate config locations on this machine:\n"
            f"{locations}\n\n"
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
            return {"ok": False, "error": http.err_text(exc)}

    def app_info(self) -> dict[str, Any]:
        return {
            "version": APP_VERSION,
            "frozen": paths.FROZEN,
            "here": str(paths.ROOT),
            "data": str(paths.DATA_DIR),
            "python": sys.executable,
            "tokens": str(paths.TOKENS_FILE),
            "calendar_tokens": str(paths.OMBIEL_TOKENS_FILE),
            "calendar_profile": str(paths.OMBIEL_PROFILE_DIR),
            "qmplus_tokens": str(paths.QMPLUS_TOKENS_FILE),
            "app_script": str(paths.APP_SCRIPT),
            "port": self._mcp_port,
            "platform": sys.platform,
        }

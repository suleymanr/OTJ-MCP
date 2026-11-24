#!/usr/bin/env python3
"""Cross-platform launcher for Timelog.

Checks the Python version, creates a local virtual environment, installs the
requirements, makes sure the MCP server is running and answering MCP requests,
then opens the desktop app. It has no dependency on OpenCode or any particular
AI client: the health check talks plain MCP over HTTP on the local port.

    python launch.py              # ensure everything, then open the app
    python launch.py --check      # check only, change nothing
    python launch.py --no-app     # ensure the MCP server for any client
    python launch.py --stop       # stop an MCP server started here
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"
MCP_SCRIPT = ROOT / "mcp_server.py"
APP_SCRIPT = ROOT / "app.py"
VENV = ROOT / ".venv"
STAMP = VENV / ".requirements.sha256"
PID_FILE = VENV / "mcp.pid"
LOG_FILE = VENV / "mcp.log"
DEFAULT_PORT = int(os.environ.get("TIMELOG_MCP_PORT", "8765"))
MIN_PYTHON = (3, 10)


def say(message: str) -> None:
    print(message, flush=True)


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr, flush=True)
    return 1


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def venv_pythonw() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "pythonw.exe"
    return venv_python()


def check_python() -> bool:
    if sys.version_info < MIN_PYTHON:
        fail(
            "Python %d.%d+ is required (found %d.%d). "
            "Install it from https://www.python.org/downloads/."
            % (*MIN_PYTHON, sys.version_info.major, sys.version_info.minor)
        )
        return False
    return True


def create_venv() -> bool:
    if venv_python().exists():
        return True
    say(f"Creating virtual environment in {VENV} ...")
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(VENV)],
            check=True,
            cwd=str(ROOT),
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        fail(f"could not create the virtual environment: {exc}")
        if sys.platform.startswith("linux"):
            print("  On Debian/Ubuntu: sudo apt install python3-venv", file=sys.stderr)
        return False
    return venv_python().exists()


def imports_ok() -> bool:
    check = "import mcp, webview, bs4, pypdf, pptx"
    return (
        subprocess.run(
            [str(venv_python()), "-c", check],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT),
        ).returncode
        == 0
    )


def requirements_hash() -> str:
    try:
        return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    except OSError:
        return ""


def install_requirements() -> bool:
    say("Installing Python requirements (this can take a minute the first time) ...")
    try:
        subprocess.run(
            [
                str(venv_python()),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(REQUIREMENTS),
            ],
            check=True,
            cwd=str(ROOT),
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        fail(f"pip install failed: {exc}")
        return False
    if not imports_ok():
        fail("requirements installed but imports still fail; try deleting .venv")
        return False
    try:
        STAMP.write_text(requirements_hash(), encoding="utf-8")
    except OSError:
        pass
    return True


def prepare_environment(allow_install: bool) -> bool:
    if not venv_python().exists():
        if not allow_install:
            fail("no virtual environment yet; run launch.cmd once without --check")
            return False
        if not create_venv():
            return False
    current = requirements_hash()
    try:
        stamped = STAMP.read_text(encoding="utf-8").strip()
    except OSError:
        stamped = ""
    if imports_ok() and stamped == current:
        say("Dependencies: OK")
        return True
    if not allow_install:
        fail("dependencies are missing; run without --no-install first")
        return False
    if not install_requirements():
        return False
    say("Dependencies: installed")
    return True


def port_open(port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def mcp_probe(port: int) -> tuple[bool, str]:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "timelog-launcher", "version": "1.0"},
            },
        }
    ).encode()
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
    try:
        conn.request(
            "POST",
            "/mcp",
            body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": "timelog-launcher",
            },
        )
        response = conn.getresponse()
        data = response.read1(4096) if hasattr(response, "read1") else response.read(4096)
        if response.status == 200 and (b'"jsonrpc"' in data or b'"result"' in data):
            return True, "MCP handshake OK"
        if response.status == 200:
            return True, "endpoint answered HTTP 200"
        if response.status in (400, 406):
            return True, f"endpoint reachable (HTTP {response.status})"
        return False, f"unexpected HTTP {response.status}"
    except (OSError, http.client.HTTPException) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        conn.close()


def tail_log(lines: int = 8) -> str:
    try:
        rows = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(rows[-lines:])


def read_pid() -> int | None:
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def process_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_mcp(port: int) -> bool:
    if not MCP_SCRIPT.exists():
        fail(f"missing {MCP_SCRIPT}")
        return False
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log = LOG_FILE.open("ab", buffering=0)
    command = [
        str(venv_python()),
        str(MCP_SCRIPT),
        "--transport",
        "http",
        "--port",
        str(port),
    ]
    kwargs = {
        "cwd": str(ROOT),
        "stdin": subprocess.DEVNULL,
        "stdout": log,
        "stderr": subprocess.STDOUT,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(command, **kwargs)
    except OSError as exc:
        fail(f"could not start the MCP server: {exc}")
        return False
    finally:
        log.close()

    for _ in range(48):
        if port_open(port):
            PID_FILE.write_text(str(proc.pid), encoding="utf-8")
            return True
        if proc.poll() is not None:
            break
        time.sleep(0.25)

    if port_open(port):
        return True
    fail("the MCP server exited before it started listening")
    details = tail_log()
    if details:
        print(details, file=sys.stderr)
    return False


def ensure_mcp(port: int, start: bool) -> int:
    if port_open(port):
        ok, detail = mcp_probe(port)
        if ok:
            say(f"MCP: running on http://127.0.0.1:{port}/mcp ({detail})")
            return 0
        say(f"MCP: port {port} is in use but did not answer MCP ({detail})")
        return 1

    if not start:
        say(f"MCP: not running on port {port}")
        return 1

    say(f"MCP: starting on http://127.0.0.1:{port}/mcp ...")
    if not start_mcp(port):
        return 1
    ok, detail = mcp_probe(port)
    if not ok:
        say(f"MCP: started but did not answer ({detail}); see {LOG_FILE}")
        return 1
    say(f"MCP: running on http://127.0.0.1:{port}/mcp ({detail})")
    return 0


def stop_mcp() -> int:
    pid = read_pid()
    if not pid:
        say("MCP: no server was started by this launcher")
        return 0
    if process_alive(pid):
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except OSError:
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
        for _ in range(20):
            if not process_alive(pid):
                break
            time.sleep(0.1)
        say(f"MCP: stopped (pid {pid})")
    else:
        say("MCP: the recorded server is no longer running")
    PID_FILE.unlink(missing_ok=True)
    return 0


def launch_app() -> int:
    if not APP_SCRIPT.exists():
        return fail(f"missing {APP_SCRIPT}")
    command = [str(venv_pythonw()), str(APP_SCRIPT)]
    kwargs = {"cwd": str(ROOT)}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen(command, **kwargs)
    except OSError as exc:
        return fail(f"could not open the app: {exc}")
    say("App: opened")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Launch Timelog")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"MCP HTTP port (default {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check Python, dependencies and MCP, but do not start anything",
    )
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="do not start the MCP server if it is down",
    )
    parser.add_argument(
        "--no-app",
        action="store_true",
        help="ensure the MCP server but do not open the desktop app",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="do not run pip; fail if requirements are missing",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="stop an MCP server started by this launcher",
    )
    args = parser.parse_args(argv)

    if args.stop:
        return stop_mcp()

    if not check_python():
        return 1

    say(f"Python: {sys.version.split()[0]}")
    if not prepare_environment(allow_install=not (args.check or args.no_install)):
        return 1

    status = ensure_mcp(args.port, start=not (args.check or args.no_start))
    if status != 0 or args.check:
        return status

    if args.no_app:
        return 0
    return launch_app()


if __name__ == "__main__":
    sys.exit(main())

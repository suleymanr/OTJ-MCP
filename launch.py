#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"
APP_SCRIPT = ROOT / "app.py"
VENV = ROOT / ".venv"
STAMP = VENV / ".requirements.sha256"
MIN_PYTHON = (3, 11)
MIN_SPLASH_SECONDS = 1.5
REPO_URL = os.environ.get("TIMELOG_REPO_URL", "https://github.com/suleymanr/OTJ-MCP.git")
REPO_BRANCH = os.environ.get("TIMELOG_REPO_BRANCH", "main")
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def venv_pythonw() -> Path:
    if os.name == "nt":
        candidate = VENV / "Scripts" / "pythonw.exe"
        if candidate.exists():
            return candidate
    return venv_python()


def _find_git() -> str | None:
    git_bin = shutil.which("git")
    if git_bin:
        return git_bin
    if os.name == "nt":
        for candidate in (
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "cmd" / "git.exe",
            Path(os.environ.get("LocalAppData", "")) / "Programs" / "Git" / "cmd" / "git.exe",
        ):
            if candidate.exists():
                return str(candidate)
    return None


def _install_git(status: Callable[[str], None]) -> str | None:
    status("Git not found. Installing Git...")
    if os.name == "nt" and shutil.which("winget"):
        subprocess.run(
            [
                "winget",
                "install",
                "--id",
                "Git.Git",
                "-e",
                "--source",
                "winget",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )
    elif sys.platform == "darwin" and shutil.which("brew"):
        subprocess.run(["brew", "install", "git"], check=False)
    elif sys.platform == "darwin":
        subprocess.run(["xcode-select", "--install"], check=False)
    return _find_git()


def _run_git(git_bin: str, *args: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [git_bin, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )


def update_via_git(status: Callable[[str], None]) -> None:
    status("Checking for updates...")
    git_bin = _find_git()
    if not git_bin:
        git_bin = _install_git(status)
    if not git_bin:
        status("Git unavailable; skipping update check.")
        return

    try:
        if not (ROOT / ".git").is_dir():
            status("Linking repository for updates...")
            _run_git(git_bin, "init", "-b", REPO_BRANCH)
            _run_git(git_bin, "remote", "add", "origin", REPO_URL)
            fetch = _run_git(git_bin, "fetch", "origin", REPO_BRANCH, timeout=30)
            if fetch.returncode == 0:
                _run_git(git_bin, "reset", "--hard", f"origin/{REPO_BRANCH}")
                status("Up to date.")
            else:
                status("Offline; continuing with local version.")
            return

        fetch = _run_git(git_bin, "fetch", "origin", REPO_BRANCH, timeout=20)
        if fetch.returncode != 0:
            status("Offline; continuing with local version.")
            return

        local = _run_git(git_bin, "rev-parse", "HEAD").stdout.strip()
        remote = _run_git(git_bin, "rev-parse", f"origin/{REPO_BRANCH}").stdout.strip()
        if local and remote and local != remote:
            status("Downloading update...")
            pull = _run_git(git_bin, "pull", "--ff-only", "origin", REPO_BRANCH, timeout=30)
            if pull.returncode == 0:
                status("Updated to latest version.")
            else:
                status("Could not fast-forward; continuing.")
        else:
            status("Already up to date.")
    except (OSError, subprocess.SubprocessError):
        status("Update check timed out; continuing.")


def ensure_venv(status: Callable[[str], None]) -> bool:
    if not venv_python().exists() or not (VENV / "pyvenv.cfg").exists():
        status("Creating virtual environment...")
        shutil.rmtree(VENV, ignore_errors=True)
        subprocess.run(
            [sys.executable, "-m", "venv", str(VENV)],
            check=True,
            cwd=str(ROOT),
            creationflags=CREATE_NO_WINDOW,
        )

    req_hash = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    stamped = STAMP.read_text(encoding="utf-8").strip() if STAMP.exists() else ""
    imports_ok = (
        subprocess.run(
            [str(venv_python()), "-c", "import mcp, webview, bs4, pypdf, pptx"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(ROOT),
            creationflags=CREATE_NO_WINDOW,
        ).returncode
        == 0
    )

    if stamped != req_hash or not imports_ok:
        status("Installing dependencies (first run may take a minute)...")
        subprocess.run(
            [str(venv_python()), "-m", "pip", "install", "--upgrade", "pip"],
            check=False,
            cwd=str(ROOT),
            creationflags=CREATE_NO_WINDOW,
        )
        subprocess.run(
            [str(venv_python()), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
            check=True,
            cwd=str(ROOT),
            creationflags=CREATE_NO_WINDOW,
        )
        STAMP.write_text(req_hash, encoding="utf-8")

    return True


def _ensure_shortcut_icon() -> None:
    if os.name != "nt":
        return
    ico = ROOT / "timelog" / "desktop" / "ui" / "icons" / "timelog.ico"
    if not ico.exists():
        return
    desired = f"{ico},0"
    for lnk in (ROOT.parent / "mcp.lnk", ROOT / "mcp.lnk"):
        if not lnk.exists():
            continue
        ps_lnk = str(lnk).replace("'", "''")
        ps_ico = desired.replace("'", "''")
        script = (
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{ps_lnk}'); "
            f"if ($s.IconLocation -ne '{ps_ico}') {{ "
            f"$s.IconLocation = '{ps_ico}'; $s.Save() }}"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )


def _run_with_splash(skip_update: bool) -> Exception | None:
    try:
        import tkinter as tk
    except Exception:
        start = time.monotonic()
        if not skip_update:
            update_via_git(lambda msg: print(msg, flush=True))
        ensure_venv(lambda msg: print(msg, flush=True))
        remaining = MIN_SPLASH_SECONDS - (time.monotonic() - start)
        if remaining > 0:
            time.sleep(remaining)
        return None

    root = tk.Tk()
    root.title("TimelogMCP")
    root.configure(bg="#141416")
    root.resizable(False, False)

    width, height = 360, 130
    sx = (root.winfo_screenwidth() - width) // 2
    sy = (root.winfo_screenheight() - height) // 2
    root.geometry(f"{width}x{height}+{sx}+{sy}")

    title_lbl = tk.Label(
        root,
        text="TimelogMCP",
        fg="#f5f5f7",
        bg="#141416",
        font=("Segoe UI" if os.name == "nt" else "Helvetica", 14, "bold"),
    )
    title_lbl.pack(pady=(26, 8))

    status_var = tk.StringVar(value="Checking for updates...")
    status_lbl = tk.Label(
        root,
        textvariable=status_var,
        fg="#a1a1aa",
        bg="#141416",
        font=("Segoe UI" if os.name == "nt" else "Helvetica", 10),
    )
    status_lbl.pack(pady=(0, 20))

    err_box: list[Exception | None] = [None]
    done = threading.Event()

    def set_status(msg: str) -> None:
        try:
            root.after(0, status_var.set, msg)
        except Exception:
            pass

    def worker() -> None:
        start = time.monotonic()
        try:
            _ensure_shortcut_icon()
            if not skip_update:
                update_via_git(set_status)
            ensure_venv(set_status)
        except Exception as exc:
            err_box[0] = exc
        finally:
            remaining = MIN_SPLASH_SECONDS - (time.monotonic() - start)
            if remaining > 0:
                time.sleep(remaining)
            done.set()
            try:
                root.after(0, root.destroy)
            except Exception:
                pass

    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()
    done.wait(timeout=1)
    return err_box[0]


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        print(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required "
            f"(found {sys.version_info.major}.{sys.version_info.minor}).",
            file=sys.stderr,
        )
        return 1

    args = sys.argv[1:]
    skip_update = "--no-update" in args
    check_only = "--check" in args

    if check_only:
        ensure_venv(lambda msg: print(msg, flush=True))
        return subprocess.run([str(venv_python()), str(APP_SCRIPT), "--check"], cwd=str(ROOT)).returncode

    err = _run_with_splash(skip_update=skip_update)
    if err is not None:
        print(f"error: {err}", file=sys.stderr)
        try:
            import tkinter as tk
            from tkinter import messagebox

            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("TimelogMCP Launch Error", str(err))
            r.destroy()
        except Exception:
            pass
        return 1

    if os.name == "nt":
        subprocess.Popen(
            [str(venv_pythonw()), str(APP_SCRIPT)],
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW | getattr(subprocess, "DETACHED_PROCESS", 0),
        )
        return 0

    os.execv(str(venv_python()), [str(venv_python()), str(APP_SCRIPT)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

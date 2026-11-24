from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from timelog.config import CREATE_NO_WINDOW, REPO_URL
from timelog.paths import APP_SCRIPT, ICON_FILE, REQUIREMENTS_FILE, ROOT, VENV_DIR, VENV_STAMP


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_pythonw() -> Path:
    if os.name == "nt":
        candidate = VENV_DIR / "Scripts" / "pythonw.exe"
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


def _run_git(git_bin: str, *args: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [git_bin, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )


def stop_running_app() -> None:
    if os.name == "nt":
        app = str(APP_SCRIPT).replace("'", "''")
        venv = str(VENV_DIR).replace("'", "''")
        script = (
            "Get-CimInstance Win32_Process | Where-Object { "
            f"$_.ProcessId -ne {os.getpid()} -and "
            f"($_.CommandLine -like '*{app}*' -or $_.ExecutablePath -like '*{venv}*') "
            "} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )
    else:
        subprocess.run(
            ["pkill", "-f", str(APP_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    time.sleep(0.3)


def update_via_git(status: Callable[[str], None]) -> None:
    status("Checking for updates...")
    git_bin = _find_git()
    if not git_bin:
        status("Git not found. Installing Git...")
        if os.name == "nt" and shutil.which("winget"):
            subprocess.run(
                [
                    "winget", "install", "--id", "Git.Git", "-e", "--source", "winget",
                    "--accept-package-agreements", "--accept-source-agreements",
                ],
                check=False,
                creationflags=CREATE_NO_WINDOW,
            )
        elif sys.platform == "darwin" and shutil.which("brew"):
            subprocess.run(["brew", "install", "git"], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["xcode-select", "--install"], check=False)
        git_bin = _find_git()
    if not git_bin:
        status("Git unavailable; skipping update check.")
        return

    try:
        if not (ROOT / ".git").is_dir():
            status("Linking repository for updates...")
            _run_git(git_bin, "init")
            _run_git(git_bin, "remote", "add", "origin", REPO_URL)

        fetch = _run_git(git_bin, "fetch", "--tags", "--force", "origin", timeout=30)
        if fetch.returncode != 0:
            status("Offline; continuing with local version.")
            return

        tags = _run_git(git_bin, "tag", "-l", "v*", "--sort=-v:refname").stdout.splitlines()
        latest = tags[0].strip() if tags else ""
        if not latest:
            status("No releases found; continuing.")
            return

        has_head = _run_git(git_bin, "rev-parse", "--verify", "HEAD").returncode == 0
        if has_head and _run_git(git_bin, "merge-base", "--is-ancestor", f"{latest}^{{commit}}", "HEAD").returncode == 0:
            status(f"Up to date ({latest}).")
            return

        status(f"Updating to {latest}...")
        stop_running_app()
        res = _run_git(git_bin, "reset", "--hard", latest, timeout=30)
        status(f"Updated to {latest}." if res.returncode == 0 else "Update failed; continuing.")
    except (OSError, subprocess.SubprocessError):
        status("Update check timed out; continuing.")


def ensure_venv(status: Callable[[str], None]) -> bool:
    if not venv_python().exists() or not (VENV_DIR / "pyvenv.cfg").exists():
        status("Creating virtual environment...")
        stop_running_app()
        shutil.rmtree(VENV_DIR, ignore_errors=True)
        subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            check=True,
            cwd=str(ROOT),
            creationflags=CREATE_NO_WINDOW,
        )

    req_hash = hashlib.sha256(REQUIREMENTS_FILE.read_bytes()).hexdigest()
    stamped = VENV_STAMP.read_text(encoding="utf-8").strip() if VENV_STAMP.exists() else ""
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
        stop_running_app()
        subprocess.run(
            [str(venv_python()), "-m", "pip", "install", "--upgrade", "pip"],
            check=False,
            cwd=str(ROOT),
            creationflags=CREATE_NO_WINDOW,
        )
        subprocess.run(
            [str(venv_python()), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
            check=True,
            cwd=str(ROOT),
            creationflags=CREATE_NO_WINDOW,
        )
        VENV_STAMP.write_text(req_hash, encoding="utf-8")

    return True


def ensure_shortcut_icon() -> None:
    if os.name != "nt" or not ICON_FILE.exists():
        return
    desired = f"{ICON_FILE},0"
    for lnk in (ROOT.parent / "mcp.lnk", ROOT / "mcp.lnk"):
        if not lnk.exists():
            continue
        ps_lnk = str(lnk).replace("'", "''")
        ps_ico = desired.replace("'", "''")
        script = (
            "$ws = New-Object -ComObject WScript.Shell; "
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

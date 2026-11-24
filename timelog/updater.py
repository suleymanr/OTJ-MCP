from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

from timelog import paths
from timelog.config import APP_VERSION, EXE_NAME, GITHUB_REPO, UA

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _parse_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for token in value.lstrip("vV").split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_update(repo: str = GITHUB_REPO) -> dict[str, Any]:
    if not repo:
        return {"ok": False, "error": "GITHUB_REPO is not configured."}

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": UA,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            release = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    latest = str(release.get("tag_name") or "").lstrip("vV")
    assets = release.get("assets") or []
    asset = next((a for a in assets if a.get("name") == EXE_NAME), None)

    return {
        "ok": True,
        "current": APP_VERSION,
        "latest": latest,
        "update_available": bool(latest) and _parse_version(latest) > _parse_version(APP_VERSION),
        "download_url": asset.get("browser_download_url") if asset else None,
        "release_url": release.get("html_url"),
    }


def apply_update(download_url: str, *, relaunch: bool = True) -> dict[str, Any]:
    if not paths.FROZEN or os.name != "nt":
        return {"ok": False, "error": "Self-update is only supported in the Windows .exe build."}

    if not download_url.startswith("https://"):
        return {"ok": False, "error": "Update URL must use HTTPS."}

    current_exe = Path(sys.executable).resolve()
    staged_exe = current_exe.with_name(f"{current_exe.stem}.new{current_exe.suffix}")

    req = urllib.request.Request(download_url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(staged_exe, "wb") as fh:
            while chunk := resp.read(65536):
                fh.write(chunk)
    except Exception as exc:
        staged_exe.unlink(missing_ok=True)
        return {"ok": False, "error": f"Download failed ({type(exc).__name__}: {exc})"}

    pid = os.getpid()
    ps_current = str(current_exe).replace("'", "''")
    ps_staged = str(staged_exe).replace("'", "''")
    relaunch_cmd = f"Start-Process -FilePath '{ps_current}';" if relaunch else ""

    # Wait for this process to exit, delete old exe, rename .new exe, then relaunch.
    script = (
        f"Wait-Process -Id {pid} -ErrorAction SilentlyContinue; "
        f"Start-Sleep -Milliseconds 300; "
        f"Remove-Item -LiteralPath '{ps_current}' -Force -ErrorAction Stop; "
        f"Move-Item -LiteralPath '{ps_staged}' -Destination '{ps_current}' -Force; "
        f"{relaunch_cmd}"
    )

    subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW | getattr(subprocess, "DETACHED_PROCESS", 0),
    )

    return {"ok": True, "restarting": True, "staged": str(staged_exe)}

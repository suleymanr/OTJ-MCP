from __future__ import annotations

import os
import sys
from pathlib import Path

from timelog.config import APP_NAME

FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", ROOT))
APP_SCRIPT = ROOT / "app.py"
REQUIREMENTS_FILE = ROOT / "requirements.txt"
VENV_DIR = ROOT / ".venv"
VENV_STAMP = VENV_DIR / ".requirements.sha256"

HOME = Path.home()
if os.name == "nt":
    APPDATA = Path(os.environ.get("APPDATA") or (HOME / "AppData" / "Roaming"))
    ZED_CONFIG_DIR = APPDATA / "Zed"
    _LOCAL_DATA = Path(os.environ.get("LOCALAPPDATA") or (HOME / "AppData" / "Local"))
elif sys.platform == "darwin":
    APPDATA = HOME / "Library" / "Application Support"
    ZED_CONFIG_DIR = HOME / ".config" / "zed"
    _LOCAL_DATA = APPDATA
else:
    APPDATA = Path(os.environ.get("XDG_CONFIG_HOME") or (HOME / ".config"))
    ZED_CONFIG_DIR = HOME / ".config" / "zed"
    _LOCAL_DATA = Path(os.environ.get("XDG_DATA_HOME") or (HOME / ".local" / "share"))

CLIENT_ROOTS: dict[str, Path] = {
    "home": HOME,
    "appdata": APPDATA,
    "zed": ZED_CONFIG_DIR,
}

if os.environ.get("TL_DATA_DIR"):
    DATA_DIR = Path(os.environ["TL_DATA_DIR"]).expanduser()
else:
    DATA_DIR = _LOCAL_DATA / APP_NAME

TOKENS_FILE = Path(os.environ.get("TL_TOKENS") or (DATA_DIR / "tokens.json")).expanduser()
PROFILE_DIR = Path(os.environ.get("TL_PROFILE") or (DATA_DIR / "browser-profile")).expanduser()
OMBIEL_TOKENS_FILE = Path(
    os.environ.get("TL_OMBIEL_TOKENS") or (DATA_DIR / "ombiel.json")
).expanduser()
OMBIEL_PROFILE_DIR = Path(
    os.environ.get("TL_OMBIEL_PROFILE") or PROFILE_DIR
).expanduser()
QMPLUS_TOKENS_FILE = Path(
    os.environ.get("TL_QMPLUS_TOKENS") or (DATA_DIR / "qmplus.json")
).expanduser()

UI_FILE = BUNDLE_DIR / "timelog" / "desktop" / "ui" / "index.html"
ICON_FILE = BUNDLE_DIR / "timelog" / "desktop" / "ui" / "icons" / "timelog.ico"
GUIDE_FILE = BUNDLE_DIR / "timelog" / "mcp" / "otj_guide.md"
MCP_LOG_FILE = DATA_DIR / "mcp.log"


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(DATA_DIR, 0o700)
        except OSError:
            pass
    return DATA_DIR


def mcp_command(*extra: str) -> list[str]:
    if FROZEN:
        return [sys.executable, "--mcp", *extra]
    return [sys.executable, str(APP_SCRIPT), "--mcp", *extra]


def auth_command(service: str, *extra: str) -> list[str]:
    if FROZEN:
        return [sys.executable, "--auth", service, *extra]
    return [sys.executable, "-m", "timelog.auth", service, *extra]

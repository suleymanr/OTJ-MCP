#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from timelog.config import APP_NAME

FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", ROOT))
SERVER_SCRIPT = ROOT / "mcp_server.py"

if os.environ.get("TL_DATA_DIR"):
    DATA_DIR = Path(os.environ["TL_DATA_DIR"]).expanduser()
elif os.name == "nt":
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / APP_NAME
elif sys.platform == "darwin":
    DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
else:
    DATA_DIR = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")) / APP_NAME

TOKENS_FILE = Path(os.environ.get("TL_TOKENS") or (DATA_DIR / "tokens.json")).expanduser()
PROFILE_DIR = Path(os.environ.get("TL_PROFILE") or (DATA_DIR / "browser-profile")).expanduser()
OMBIEL_TOKENS_FILE = Path(os.environ.get("TL_OMBIEL_TOKENS") or (DATA_DIR / "ombiel.json")).expanduser()
OMBIEL_PROFILE_DIR = Path(os.environ.get("TL_OMBIEL_PROFILE") or PROFILE_DIR).expanduser()
QMPLUS_TOKENS_FILE = Path(os.environ.get("TL_QMPLUS_TOKENS") or (DATA_DIR / "qmplus.json")).expanduser()


def mcp_command(*extra: str) -> list[str]:
    if FROZEN:
        return [sys.executable, "--mcp", *extra]
    return [sys.executable, str(SERVER_SCRIPT), *extra]


def browser_command(service: str, *extra: str) -> list[str]:
    if FROZEN:
        return [sys.executable, "--browser", service, *extra]
    return [sys.executable, "-m", "timelog.browser.auth", service, *extra]


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if os.name != "nt":
        # Owner-only permissions for the credential directory.
        try:
            os.chmod(DATA_DIR, 0o700)
        except OSError:
            pass

    return DATA_DIR


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def write_json(
    path: str | Path,
    data: Any,
    *,
    indent: int | None = 2,
    mode: int | None = None,
) -> None:
    ensure_data_dir()

    target = Path(path)
    tmp = str(target) + ".tmp"

    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent)

    os.replace(tmp, target)

    if mode is not None and os.name != "nt":
        try:
            os.chmod(target, mode)
        except OSError:
            pass


def jwt_claims(token: str) -> dict[str, Any]:
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(part))
        return decoded if isinstance(decoded, dict) else {}
    except Exception:
        return {}


def jwt_exp(token: str) -> int:
    try:
        return int(jwt_claims(token).get("exp", 0))
    except (TypeError, ValueError):
        return 0


def _move(src: Path, dst: Path) -> bool:
    if not src.exists() or dst.exists():
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.move(str(src), str(dst))
    except Exception:
        try:
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                shutil.rmtree(src, ignore_errors=True)
            else:
                shutil.copy2(src, dst)
                src.unlink(missing_ok=True)
        except Exception:
            return False

    return True


def migrate_legacy() -> list[str]:
    if os.environ.get("TL_NO_MIGRATE") == "1":
        return []

    moved: list[str] = []
    for src, dst in (
        (ROOT / "tokens.json", TOKENS_FILE),
        (ROOT / ".browser-profile", PROFILE_DIR),
    ):
        if src.exists() and not dst.exists() and _move(src, dst):
            moved.append(str(dst))

    return moved


ensure_data_dir()
migrate_legacy()

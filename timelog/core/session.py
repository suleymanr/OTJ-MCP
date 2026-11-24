from __future__ import annotations

import base64
import datetime as dt
import json
import os
import time
from pathlib import Path
from typing import Any

from timelog import paths
from timelog.config import JWT_SKEW_S, OMBIEL_COOKIES, QMPLUS_COOKIES


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


def format_exp(exp: int) -> str | None:
    if not exp:
        return None
    return dt.datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M")


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
    mode: int | None = 0o600,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = f"{target}.tmp"

    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent)

    os.replace(tmp, target)
    if mode is not None and os.name != "nt":
        try:
            os.chmod(target, mode)
        except OSError:
            pass


class SessionStore:
    def __init__(self, path: Path, cookie_names: frozenset[str] = frozenset()) -> None:
        self.path = path
        self.cookie_names = cookie_names

    def load(self) -> dict[str, Any]:
        data = read_json(self.path, {})
        return data if isinstance(data, dict) else {}

    def save(self, data: dict[str, Any], *, indent: int | None = 2) -> None:
        write_json(self.path, data, indent=indent, mode=0o600)

    def save_cookies(
        self,
        cookies: list[dict[str, Any]] | None,
        *,
        extra: dict[str, Any] | None = None,
        source: str = "webview",
    ) -> dict[str, Any]:
        data = self.load()
        for cookie in cookies or []:
            name = cookie.get("name")
            value = cookie.get("value")
            if name in self.cookie_names and value:
                data[name] = value

        if extra:
            for key, value in extra.items():
                if value is not None:
                    data[key] = value

        data["saved_at"] = int(time.time())
        data["source"] = source
        self.save(data)
        return data

    def jwt_status(
        self,
        token_key: str,
        *,
        skew: int = JWT_SKEW_S,
    ) -> tuple[bool, int, str | None, dict[str, Any]]:
        token = self.load().get(token_key)
        if not token:
            return False, 0, None, {}

        claims = jwt_claims(token)
        exp = int(claims.get("exp") or 0)
        remaining = max(0, exp - int(time.time())) if exp else 0
        return exp - time.time() > skew, remaining, format_exp(exp), claims


TIMELOG_STORE = SessionStore(paths.TOKENS_FILE)
CALENDAR_STORE = SessionStore(paths.OMBIEL_TOKENS_FILE, OMBIEL_COOKIES)
QMPLUS_STORE = SessionStore(paths.QMPLUS_TOKENS_FILE, QMPLUS_COOKIES)

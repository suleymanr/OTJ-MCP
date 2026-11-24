#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from timelog import paths
from timelog.config import API_BASE, API_ORIGIN, CLIENT_ID, TOKEN_URL, TYPE_BY_NAME, UA

TOKENS_FILE = str(paths.TOKENS_FILE)


def _exp_text(exp: int) -> str | None:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(exp)) if exp else None


def token_state(token_file: str = TOKENS_FILE) -> dict[str, Any]:
    data = paths.read_json(token_file, {}) or {}
    now = int(time.time())
    at = data.get("access_token")
    rt = data.get("refresh_token")

    claims = paths.jwt_claims(at) if at else {}
    if not claims and rt:
        claims = paths.jwt_claims(rt)

    access_in = max(0, paths.jwt_exp(at) - now) if at else 0
    refresh_in = max(0, paths.jwt_exp(rt) - now) if rt else 0

    return {
        "connected": access_in > 0 or refresh_in > 0,
        "has_access": bool(at),
        "access_expires_in": access_in,
        "access_expires_at": _exp_text(paths.jwt_exp(at)) if at else None,
        "has_refresh": bool(rt),
        "refresh_expires_in": refresh_in,
        "refresh_expires_at": _exp_text(paths.jwt_exp(rt)) if rt else None,
        "source": data.get("source", "refresh-grant"),
        "tokens_file": token_file,
        "email": claims.get("email") or claims.get("preferred_username"),
        "name": claims.get("name"),
    }


class Auth:
    def __init__(self, token_file: str = TOKENS_FILE) -> None:
        self.token_file = token_file
        if not os.path.exists(token_file):
            raise SystemExit(
                f"No token file at {token_file}.\n"
                "Open the Timelog app and sign in."
            )

        self.data: dict[str, Any] = paths.read_json(token_file, {})

    def _reload(self) -> None:
        disk = paths.read_json(self.token_file)
        if not isinstance(disk, dict):
            return

        if (
            disk.get("access_token") != self.data.get("access_token")
            or disk.get("refresh_token") != self.data.get("refresh_token")
        ):
            self.data = disk

    def _refresh_token_ok(self, skew: int = 30) -> bool:
        rt = self.data.get("refresh_token")
        return bool(rt and paths.jwt_exp(rt) - time.time() > skew)

    def refresh(self) -> str:
        self._reload()

        # A dead refresh token only costs a round-trip and hides the real path.
        if not self._refresh_token_ok():
            if self._browser_refresh():
                return self.data["access_token"]
            raise RuntimeError(
                "Token refresh failed: the refresh token has expired and the "
                "browser session is signed out.\n"
                "Open the Timelog app and sign in again."
            )

        body = urllib.parse.urlencode(
            {
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "refresh_token": self.data["refresh_token"],
            }
        ).encode()

        req = urllib.request.Request(
            TOKEN_URL,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": UA,
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                new = json.load(resp)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            # Refresh token rejected: try the persistent browser session via /refreshauth.
            if self._browser_refresh():
                return self.data["access_token"]
            raise RuntimeError(
                "Token refresh failed and the browser session is not logged in.\n"
                "Open the Timelog app and sign in again.\n"
                f"(server said: {detail})"
            ) from None
        except Exception as exc:
            if self._browser_refresh():
                return self.data["access_token"]
            raise RuntimeError(
                f"Token refresh failed ({type(exc).__name__}: {exc}).\n"
                "Open the Timelog app and sign in again."
            ) from None

        self.data["access_token"] = new["access_token"]
        self.data["refresh_token"] = new["refresh_token"]
        self.data["expires_in"] = new.get("expires_in")
        self.data["refresh_expires_in"] = new.get("refresh_expires_in")
        self.data["obtained_at"] = int(time.time())
        self.data["source"] = "refresh-grant"
        paths.write_json(self.token_file, self.data, indent=None)

        return new["access_token"]

    def _browser_refresh(self) -> bool:
        import subprocess

        flags = 0x08000000 if os.name == "nt" else 0
        try:
            res = subprocess.run(
                paths.browser_command("refresh"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=45,
                creationflags=flags,
            )
            if res.returncode == 0:
                self.data = paths.read_json(paths.TOKENS_FILE, {})
                return bool(self.data.get("access_token"))
        except Exception:
            return False

        return False

    def ensure_valid(self, skew: int = 60) -> str:
        self._reload()

        tok = self.data.get("access_token")
        if tok and paths.jwt_exp(tok) - time.time() > skew:
            return tok

        return self.refresh()


class Timelog:
    def __init__(self, auth: Auth | None = None) -> None:
        self.auth = auth or Auth()
        self._profile: dict[str, Any] | None = None

    def _request(self, path: str, method: str = "GET", body: Any = None) -> Any:
        token = self.auth.ensure_valid()

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            # The API authenticates via ACCESS_TOKEN cookie; the browser also sends an empty Bearer header.
            "Authorization": "Bearer ",
            "Cookie": "ACCESS_TOKEN=" + token,
            "Origin": API_ORIGIN,
            "Referer": API_ORIGIN + "/cloud-education/timelog",
            "User-Agent": UA,
        }
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{API_BASE}/{path.lstrip('/')}",
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            # A 401 means the cached access token was rejected: refresh once.
            if exc.code == 401:
                self.auth.refresh()
                return self._request(path, method, body)
            raise RuntimeError(f"HTTP {exc.code} on {method} {path}: {raw}") from None

    @property
    def profile(self) -> dict[str, Any]:
        if self._profile is None:
            self._profile = self._request("account/user-profile")
        return self._profile

    @property
    def learner_id(self) -> Any:
        return self.profile["smartLearnerId"]

    @property
    def unit_id(self) -> Any:
        return self.profile.get("unitId") or self._request(
            f"learner/{self.learner_id}/main-aim"
        ).get("unitID")

    def activity_types(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        return self._request(
            f"lists/activity-types/{'true' if include_inactive else 'false'}"
        )

    def list_entries(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        return self._request(
            f"learner/{self.learner_id}/off-the-job"
            f"?fromDate={date_from}&toDate={date_to}"
        )

    def add_entry(
        self,
        activity_date: str,
        start_time: str,
        hours: int,
        minutes: int,
        activity_type: int | str,
        impact: str,
        unit_id: str | None = None,
    ) -> Any:
        if start_time.count(":") == 1:
            start_time += ":00"

        if isinstance(activity_type, str):
            key = activity_type.strip().lower()
            if key.isdigit():
                activity_type = int(key)
            elif key in TYPE_BY_NAME:
                activity_type = TYPE_BY_NAME[key]
            else:
                raise ValueError("Unknown activity type.")

        payload = {
            "learnerId": self.learner_id,
            "unitId": unit_id or self.unit_id,
            "activityDate": activity_date,
            "activityTime": start_time,
            "activityType": int(activity_type),
            "activityImpact": impact,
            "hours": str(hours).zfill(2),
            "minutes": str(minutes).zfill(2),
        }

        return self._request(f"learner/{self.learner_id}/activity-log", "POST", payload)

    def delete_entry(self, entry_id: int) -> Any:
        return self._request(
            f"learner/{self.learner_id}/activity-log/{entry_id}", "DELETE"
        )

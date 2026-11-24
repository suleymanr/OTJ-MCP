from __future__ import annotations

import subprocess
import time
import urllib.parse
from typing import Any

from timelog import paths
from timelog.config import (
    ACTIVITY_TYPES,
    API_BASE,
    API_ORIGIN,
    CLIENT_ID,
    JWT_SKEW_S,
    REFRESH_SKEW_S,
    TIMELOG_START_URL,
    TOKEN_TIMEOUT_S,
    TOKEN_URL,
    TYPE_BY_NAME,
)
from timelog.core import http
from timelog.core.http import AuthRequired, ServiceError
from timelog.core.session import (
    TIMELOG_STORE,
    SessionStore,
    format_exp,
    jwt_claims,
    jwt_exp,
)


def token_state(store: SessionStore = TIMELOG_STORE) -> dict[str, Any]:
    data = store.load()
    now = int(time.time())
    at = data.get("access_token")
    rt = data.get("refresh_token")

    claims = jwt_claims(at) if at else {}
    if not claims and rt:
        claims = jwt_claims(rt)

    at_exp = jwt_exp(at) if at else 0
    rt_exp = jwt_exp(rt) if rt else 0
    access_in = max(0, at_exp - now) if at_exp else 0
    refresh_in = max(0, rt_exp - now) if rt_exp else 0

    return {
        "connected": access_in > 0 or refresh_in > 0,
        "has_access": bool(at),
        "access_expires_in": access_in,
        "access_expires_at": format_exp(at_exp),
        "has_refresh": bool(rt),
        "refresh_expires_in": refresh_in,
        "refresh_expires_at": format_exp(rt_exp),
        "source": data.get("source", "refresh-grant"),
        "tokens_file": str(store.path),
        "email": claims.get("email") or claims.get("preferred_username"),
        "name": claims.get("name"),
    }


def save_cookies(
    cookies: list[dict[str, str]],
    store: SessionStore = TIMELOG_STORE,
) -> bool:
    by_name = {c["name"]: c["value"] for c in cookies if c.get("name") and c.get("value")}
    access = by_name.get("ACCESS_TOKEN")
    refresh = by_name.get("REFRESH_TOKEN")
    if not access:
        return False

    data = store.load()
    data["access_token"] = access
    if refresh:
        data["refresh_token"] = refresh
    elif data.get("refresh_token") and jwt_exp(data["refresh_token"]) <= time.time():
        data["refresh_token"] = None

    data["obtained_at"] = int(time.time())
    data["source"] = "webview"
    store.save(data)
    return True


def resolve_activity_type(activity_type: str | int | None) -> tuple[int | None, str | None]:
    if activity_type is None:
        return None, None

    raw = str(activity_type).strip()
    if not raw:
        return None, None

    if raw.isdigit():
        tid = int(raw)
        if tid in ACTIVITY_TYPES:
            return tid, ACTIVITY_TYPES[tid]
        return None, None

    tid = TYPE_BY_NAME.get(raw.lower())
    if tid is not None:
        return tid, ACTIVITY_TYPES[tid]

    return None, None


def validate_entry(
    date: str,
    start_time: str,
    hours: int,
    minutes: int,
    activity_type: str | int,
    impact: str,
) -> dict[str, Any]:
    issues: list[str] = []
    questions: list[str] = []

    if not (date or "").strip():
        issues.append("date is missing")
        questions.append("What date was the activity? (YYYY-MM-DD)")

    if not (start_time or "").strip():
        issues.append("start time is missing")
        questions.append("What time did it start? (HH:MM, 24-hour)")

    try:
        h, m = int(hours or 0), int(minutes or 0)
    except (TypeError, ValueError):
        h = m = 0

    if h <= 0 and m <= 0:
        issues.append("duration is missing or zero")
        questions.append("How long did it last? (hours and minutes)")

    tid, name = resolve_activity_type(activity_type)
    if tid is None:
        if activity_type in (None, ""):
            issues.append("activity type is missing")
        else:
            issues.append(f"unknown activity type: {activity_type!r}")
        questions.append(
            "Which activity type fits best: 13 face-to-face, 1 virtual, "
            "16 self-study, 17 mentoring/coaching, 19 learning by doing your "
            "job, 20 review/feedback, 22 other?"
        )
    elif tid == 23:
        issues.append("Furloughed is not off-the-job training")
        questions.append(
            "What learning did you do during paid hours that relates to your standard?"
        )

    text = (impact or "").strip()
    if not text:
        issues.append("impact/reflection is missing")
        questions.append(
            "What did you learn, and how does it link to your standard or KSBs?"
        )
    elif len(text) < 20:
        issues.append("impact/reflection is too short (minimum 20 characters)")
        questions.append(
            "Can you add a sentence on what you learned and how you will use it?"
        )

    return {
        "ready": not issues,
        "issues": issues,
        "questions": questions,
        "activityTypeId": tid,
        "activityTypeName": name,
    }


class Auth:
    def __init__(self, store: SessionStore = TIMELOG_STORE) -> None:
        self.store = store
        self.data = store.load()
        if not self.data:
            raise AuthRequired("Timelog is not connected. Open the Timelog app and sign in.")

    def _reload(self) -> None:
        disk = self.store.load()
        if (
            disk.get("access_token") != self.data.get("access_token")
            or disk.get("refresh_token") != self.data.get("refresh_token")
        ):
            self.data = disk

    def _refresh_token_ok(self, skew: int = REFRESH_SKEW_S) -> bool:
        rt = self.data.get("refresh_token")
        return bool(rt and jwt_exp(rt) - time.time() > skew)

    def _browser_refresh(self) -> bool:
        try:
            res = subprocess.run(
                paths.auth_command("refresh"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=45,
                creationflags=http.subprocess_flags(),
            )
            if res.returncode == 0:
                self.data = self.store.load()
                return bool(self.data.get("access_token"))
        except Exception:
            return False
        return False

    def refresh(self) -> str:
        self._reload()

        if not self._refresh_token_ok():
            if self._browser_refresh():
                return self.data["access_token"]
            raise AuthRequired(
                "Timelog session expired. Open the Timelog app and sign in again."
            )

        encoded = urllib.parse.urlencode(
            {
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "refresh_token": self.data["refresh_token"],
            }
        ).encode("utf-8")

        try:
            new = http.request_json(
                TOKEN_URL,
                method="POST",
                data=encoded,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                timeout=TOKEN_TIMEOUT_S,
            )
        except ServiceError:
            if self._browser_refresh():
                return self.data["access_token"]
            raise AuthRequired(
                "Token refresh failed and the browser session is signed out. "
                "Open the Timelog app and sign in again."
            ) from None

        self.data["access_token"] = new["access_token"]
        self.data["refresh_token"] = new["refresh_token"]
        self.data["expires_in"] = new.get("expires_in")
        self.data["refresh_expires_in"] = new.get("refresh_expires_in")
        self.data["obtained_at"] = int(time.time())
        self.data["source"] = "refresh-grant"
        self.store.save(self.data, indent=None)
        return new["access_token"]

    def ensure_valid(self, skew: int = JWT_SKEW_S) -> str:
        self._reload()
        tok = self.data.get("access_token")
        if tok and jwt_exp(tok) - time.time() > skew:
            return tok
        return self.refresh()


class TimelogClient:
    def __init__(self, auth: Auth | None = None) -> None:
        self.auth = auth or Auth()
        self._profile: dict[str, Any] | None = None

    def _request(self, path: str, method: str = "GET", body: Any = None) -> Any:
        token = self.auth.ensure_valid()
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            # OneAdvanced authenticates via ACCESS_TOKEN cookie and expects an empty Bearer header.
            "Authorization": "Bearer ",
            "Cookie": f"ACCESS_TOKEN={token}",
            "Origin": API_ORIGIN,
            "Referer": TIMELOG_START_URL,
        }
        url = f"{API_BASE}/{path.lstrip('/')}"
        try:
            return http.request_json(url, method=method, headers=headers, body=body)
        except AuthRequired:
            token = self.auth.refresh()
            headers["Cookie"] = f"ACCESS_TOKEN={token}"
            return http.request_json(url, method=method, headers=headers, body=body)

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
        flag = "true" if include_inactive else "false"
        return self._request(f"lists/activity-types/{flag}") or []

    def list_entries(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        return (
            self._request(
                f"learner/{self.learner_id}/off-the-job?fromDate={date_from}&toDate={date_to}"
            )
            or []
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

        tid, _ = resolve_activity_type(activity_type)
        if tid is None:
            raise ValueError("Unknown activity type.")

        payload = {
            "learnerId": self.learner_id,
            "unitId": unit_id or self.unit_id,
            "activityDate": activity_date,
            "activityTime": start_time,
            "activityType": tid,
            "activityImpact": impact,
            "hours": str(hours).zfill(2),
            "minutes": str(minutes).zfill(2),
        }
        return self._request(f"learner/{self.learner_id}/activity-log", "POST", payload)

    def delete_entry(self, entry_id: int) -> Any:
        return self._request(f"learner/{self.learner_id}/activity-log/{entry_id}", "DELETE")

    def totals(self) -> Any:
        return self._request(f"learner/{self.learner_id}/off-the-job-totals")

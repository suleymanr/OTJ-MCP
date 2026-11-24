from __future__ import annotations

import datetime as dt
import urllib.parse
from typing import Any

from timelog.config import (
    CAL2_PATH,
    CALENDAR_TIMEOUT_S,
    CALENDARS_PATH,
    OMBIEL_BASE,
    OMBIEL_HOME,
)
from timelog.core import http
from timelog.core.http import AuthRequired, ServiceError
from timelog.core.session import CALENDAR_STORE, jwt_exp


def save_cookies(
    cookies: list[dict[str, Any]] | None,
    source: str = "webview",
) -> dict[str, Any]:
    CALENDAR_STORE.save_cookies(cookies, source=source)
    return token_state()


def token_state() -> dict[str, Any]:
    connected, remaining, expires_at, claims = CALENDAR_STORE.jwt_status("cmAuthToken")
    if not claims and not CALENDAR_STORE.load().get("cmAuthToken"):
        return {"connected": False, "has_token": False, "expires_in": 0}

    return {
        "connected": connected,
        "has_token": True,
        "expires_in": remaining,
        "expires_at": expires_at,
        "username": claims.get("username"),
        "mail": claims.get("mail"),
        "person_id": claims.get("cmPersonId"),
        "org_code": claims.get("cmOrgCode"),
        "profile_group_id": claims.get("cmProfileGroupId"),
    }


def _date_start(value: str | dt.datetime) -> str:
    if isinstance(value, dt.datetime):
        return value.strftime("%Y-%m-%dT00:00:00.000Z")
    return f"{value}T00:00:00.000Z"


def _date_end(value: str | dt.datetime) -> str:
    base = value.date() if isinstance(value, dt.datetime) else dt.date.fromisoformat(value)
    return (base + dt.timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")


def _normalise(event: dict[str, Any], calendar: str) -> dict[str, Any]:
    return {
        "id": event.get("eventRef"),
        "calendar": calendar,
        "title": event.get("desc1") or event.get("desc2") or "",
        "description": event.get("desc2") or event.get("desc3") or "",
        "location": event.get("location") or event.get("locationName") or "",
        "start": event.get("start") or event.get("calDate") or "",
        "end": event.get("end") or "",
        "allDay": str(event.get("isAllDay", "")).lower() == "true",
    }


class CalendarClient:
    def __init__(self) -> None:
        self.data = CALENDAR_STORE.load()

    @property
    def token(self) -> str:
        token = self.data.get("cmAuthToken")
        if not token:
            raise AuthRequired(
                "Calendar is not connected. Open the app and click 'Connect'."
            )

        exp = jwt_exp(token)
        if exp and exp - dt.datetime.now().timestamp() <= 60:
            raise AuthRequired("Calendar session has expired. Reconnect it in the app.")
        return token

    def _request(self, path: str, params: dict[str, str] | None = None) -> Any:
        url = f"{OMBIEL_BASE}/{path.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        return http.request_json(
            url,
            headers={
                "Accept": "application/json",
                "Cookie": f"cmAuthToken={self.token}",
                "Referer": OMBIEL_HOME,
            },
            timeout=CALENDAR_TIMEOUT_S,
            auth_message="Calendar session rejected. Reconnect it in the app.",
        )

    def calendars(self) -> list[dict[str, Any]]:
        data = self._request(CALENDARS_PATH)
        return data.get("calendars", []) if isinstance(data, dict) else []

    def events(
        self,
        calendar: str,
        from_date: str | dt.datetime,
        to_date: str | dt.datetime,
    ) -> list[dict[str, Any]]:
        data = self._request(
            CAL2_PATH + urllib.parse.quote(calendar, safe=""),
            {"start": _date_start(from_date), "end": _date_end(to_date)},
        )
        events = data.get("events", []) if isinstance(data, dict) else []
        return [_normalise(e, calendar) for e in events]

    def range_events(
        self,
        from_date: str,
        to_date: str,
        calendar: str | None = None,
    ) -> list[dict[str, Any]]:
        cal_names = (
            [calendar]
            if calendar
            else [c["calType"] for c in self.calendars() if c.get("calType")]
        )

        collected: list[dict[str, Any]] = []
        for name in cal_names:
            try:
                collected.extend(self.events(name, from_date, to_date))
            except AuthRequired:
                raise
            except ServiceError:
                continue

        seen: set[tuple[Any, Any, Any]] = set()
        unique: list[dict[str, Any]] = []
        for event in sorted(collected, key=lambda x: (x.get("start") or "", x.get("title") or "")):
            key = (event.get("start"), event.get("end"), event.get("title"))
            if key not in seen:
                seen.add(key)
                unique.append(event)
        return unique

    def upcoming(self, days: int = 7) -> list[dict[str, Any]]:
        today = dt.date.today()
        end = today + dt.timedelta(days=max(1, int(days)))
        return self.range_events(today.isoformat(), end.isoformat())

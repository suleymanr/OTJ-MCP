#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from timelog import paths
from timelog.config import CAL2_PATH, CALENDARS_PATH, OMBIEL_BASE, OMBIEL_HOME, UA
from timelog.server.modules.schemas import CalendarAuthRequired, CalendarError


def read_tokens() -> dict[str, Any]:
    data = paths.read_json(paths.OMBIEL_TOKENS_FILE, {})
    return data if isinstance(data, dict) else {}


def save_cookies(cookies: list[dict[str, Any]] | None, source: str = "browser") -> dict[str, Any]:
    wanted = {"cmAuthToken", "a", "__a"}
    data = read_tokens()

    for c in cookies or []:
        name = c.get("name")
        if name in wanted and c.get("value"):
            data[name] = c["value"]

    data["saved_at"] = int(time.time())
    data["source"] = source
    paths.write_json(paths.OMBIEL_TOKENS_FILE, data, mode=0o600)

    return token_state()


def token_state() -> dict[str, Any]:
    data = read_tokens()
    token = data.get("cmAuthToken")
    if not token:
        return {"connected": False, "has_token": False, "expires_in": 0}

    claims = paths.jwt_claims(token)
    exp = int(claims.get("exp", 0))
    now = int(time.time())

    return {
        "connected": exp - now > 60,
        "has_token": True,
        "expires_in": max(0, exp - now),
        "expires_at": (
            dt.datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M") if exp else None
        ),
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
        self.data = read_tokens()

    @property
    def token(self) -> str:
        token = self.data.get("cmAuthToken")
        if not token:
            raise CalendarAuthRequired(
                "Calendar is not connected. Open the app and click "
                "'Connect calendar'."
            )

        exp = paths.jwt_exp(token)
        if exp and exp - time.time() <= 60:
            raise CalendarAuthRequired(
                "Calendar session has expired. Reconnect it in the app."
            )

        return token

    def _request(self, path: str, params: dict[str, str] | None = None) -> Any:
        url = f"{OMBIEL_BASE}/{path.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Cookie": "cmAuthToken=" + self.token,
                "Referer": OMBIEL_HOME,
                "User-Agent": UA,
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            if exc.code in (401, 403):
                raise CalendarAuthRequired(
                    "Calendar session rejected. Reconnect it in the app. "
                    f"({body[:160]})"
                ) from None
            raise CalendarError(f"HTTP {exc.code} on {path}: {body[:200]}") from None
        except Exception as exc:
            raise CalendarError(f"{type(exc).__name__}: {exc}") from None

        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            raise CalendarError(f"Unexpected response from {path}") from None

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
            {
                "start": _date_start(from_date),
                "end": _date_end(to_date),
            },
        )
        events = data.get("events", []) if isinstance(data, dict) else []
        return [_normalise(e, calendar) for e in events]

    def range_events(
        self,
        from_date: str,
        to_date: str,
        calendar: str | None = None,
    ) -> list[dict[str, Any]]:
        calendars = [calendar] if calendar else [
            c["calType"] for c in self.calendars() if c.get("calType")
        ]

        out: list[dict[str, Any]] = []
        for name in calendars:
            try:
                out.extend(self.events(name, from_date, to_date))
            except CalendarAuthRequired:
                raise
            except CalendarError:
                continue

        seen: set[tuple[Any, Any, Any]] = set()
        unique: list[dict[str, Any]] = []
        for e in sorted(out, key=lambda x: (x.get("start") or "", x.get("title") or "")):
            key = (e.get("start"), e.get("end"), e.get("title"))
            if key not in seen:
                seen.add(key)
                unique.append(e)

        return unique

    def upcoming(self, days: int = 7) -> list[dict[str, Any]]:
        today = dt.date.today()
        end = today + dt.timedelta(days=max(1, int(days)))
        return self.range_events(today.isoformat(), end.isoformat())

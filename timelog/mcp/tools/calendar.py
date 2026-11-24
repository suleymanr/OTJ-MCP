from __future__ import annotations

import datetime as dt
from typing import Any

from mcp.server.mcpserver import MCPServer

from timelog.mcp.tools import call
from timelog.services import calendar as calendar_svc


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def calendar_status() -> dict[str, Any]:
        """Check whether the CampusM calendar is connected and when its token expires."""
        return await call(lambda: {"ok": True, **calendar_svc.token_state()})

    @mcp.tool()
    async def calendar_list() -> dict[str, Any]:
        """List the user's CampusM calendars (e.g. Course Timetable)."""
        def _fetch() -> dict[str, Any]:
            calendars = calendar_svc.CalendarClient().calendars()
            return {"ok": True, "count": len(calendars), "calendars": calendars}

        return await call(_fetch)

    @mcp.tool()
    async def calendar_events(
        calendar: str = "",
        from_date: str = "",
        to_date: str = "",
    ) -> dict[str, Any]:
        """List calendar events between two ISO dates (YYYY-MM-DD)."""
        today = dt.date.today()
        start = from_date or today.isoformat()
        end = to_date or (today + dt.timedelta(days=7)).isoformat()

        def _fetch() -> dict[str, Any]:
            events = calendar_svc.CalendarClient().range_events(start, end, calendar or None)
            return {
                "ok": True,
                "from": start,
                "to": end,
                "count": len(events),
                "events": events,
            }

        return await call(_fetch)

    @mcp.tool()
    async def calendar_upcoming(days: int = 7) -> dict[str, Any]:
        """Upcoming classes/events for the next N days (1-90)."""
        clamped = max(1, min(int(days), 90))
        return await call(
            lambda: (
                lambda events: {
                    "ok": True,
                    "days": clamped,
                    "count": len(events),
                    "events": events,
                }
            )(calendar_svc.CalendarClient().upcoming(clamped))
        )

from __future__ import annotations

import datetime as dt
from typing import Any

from mcp.server.mcpserver import MCPServer

from timelog.mcp.tools import call
from timelog.services import calendar as calendar_svc
from timelog.services import qmplus as qmplus_svc


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def qmplus_status() -> dict[str, Any]:
        """Check whether QMplus is connected."""
        return await call(lambda: {"ok": True, **qmplus_svc.session_state()})

    @mcp.tool()
    async def qmplus_courses() -> dict[str, Any]:
        """List the user's enrolled QMplus modules (course id, name, code)."""
        def _fetch() -> dict[str, Any]:
            courses = qmplus_svc.QmplusClient().courses()
            return {"ok": True, "count": len(courses), "courses": courses}

        return await call(_fetch)

    @mcp.tool()
    async def qmplus_course_contents(course_id: int) -> dict[str, Any]:
        """Get sections and activities for a QMplus module (compact list)."""
        def _fetch() -> dict[str, Any]:
            contents = qmplus_svc.QmplusClient().course_contents(course_id)
            sections: list[dict[str, Any]] = []
            count = 0
            for section in contents.get("sections", []):
                acts = section.get("activities") or []
                if not acts:
                    continue
                rows = [
                    {"name": a.get("name"), "modname": a.get("modname"), "url": a.get("url")}
                    for a in acts
                ]
                count += len(rows)
                sections.append({"name": section.get("name"), "activities": rows})
            return {
                "ok": True,
                "course_id": contents.get("course_id"),
                "title": contents.get("title"),
                "url": contents.get("url"),
                "sections": sections,
                "activity_count": count,
            }

        return await call(_fetch)

    @mcp.tool()
    async def qmplus_search(
        course_id: int,
        query: str,
        deep: bool = False,
    ) -> dict[str, Any]:
        """Search a module's sections/activities/files. deep=True also searches PDF/PPTX text."""
        return await call(
            lambda: {"ok": True, **qmplus_svc.QmplusClient().search(course_id, query, deep)}
        )

    @mcp.tool()
    async def qmplus_fetch(
        activity_url: str = "",
        course_id: int = 0,
        query: str = "",
    ) -> dict[str, Any]:
        """Fetch a module resource by URL, or by course_id + search query."""
        def _fetch() -> dict[str, Any]:
            client = qmplus_svc.QmplusClient()
            target = activity_url
            if not target and course_id and query:
                found = client.search(course_id, query, False)
                target = next(
                    (item["url"] for item in found.get("results", []) if item.get("url")),
                    "",
                )
            if not target:
                raise ValueError("Provide activity_url, or course_id + query")
            return client.fetch_url(target)

        return await call(_fetch)

    @mcp.tool()
    async def qmplus_current_lecture() -> dict[str, Any]:
        """Find the class in progress from the CampusM timetable and the matching QMplus module."""
        def _fetch() -> dict[str, Any]:
            today = dt.date.today().isoformat()
            try:
                events = calendar_svc.CalendarClient().range_events(today, today)
            except Exception:
                events = []

            now = dt.datetime.now().astimezone()
            current: dict[str, Any] | None = None
            upcoming: dict[str, Any] | None = None

            for event in events:
                try:
                    start = dt.datetime.fromisoformat(event["start"])
                    end = dt.datetime.fromisoformat(event["end"]) if event.get("end") else start
                except Exception:
                    continue
                if start <= now <= end:
                    current = event
                    break
                if start > now and (
                    upcoming is None or start < dt.datetime.fromisoformat(upcoming["start"])
                ):
                    upcoming = event

            chosen = current or upcoming
            if not chosen:
                return {"ok": False, "error": "No current or upcoming class found in CampusM today."}
            return qmplus_svc.QmplusClient().match_event(chosen)

        return await call(_fetch)

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import traceback
from typing import Any, Callable

import anyio
from mcp.server.mcpserver import MCPServer

from timelog import paths
from timelog.config import APP_VERSION, DEFAULT_PORT
from timelog.server.modules import (
    calendar as ombiel_calendar,
    client as timelog,
    qmplus as qmplus_client,
)
from timelog.server.modules.schemas import AuthRequired, validate_entry

_DEBUG = os.environ.get("TIMELOG_MCP_DEBUG") == "1"
GUIDE_PATH = paths.BUNDLE_DIR / "timelog" / "server" / "otj_guide.md"

try:
    with open(GUIDE_PATH, "r", encoding="utf-8") as _fh:
        OTJ_GUIDE = _fh.read()
except OSError:
    OTJ_GUIDE = (
        "Off-the-job (OTJ) training is learning during paid hours, outside "
        "normal duties, directly relevant to the apprenticeship standard. "
        "Ask for date, start time, duration, activity type and a specific "
        "reflection before logging."
    )

mcp = MCPServer(
    name="timelog",
    title="Cloud Education Timelog",
    instructions=(
        "Use this server to read and write off-the-job (OTJ) timelog entries for "
        "the signed-in learner on OneAdvanced Cloud Education.\n\n"
        "AUTH CHECK FIRST: before starting any chain of tool calls, call "
        "`auth_status` if login states have not been checked in the last 15 "
        "minutes. If any required service (timelog, calendar, or qmplus) is "
        "disconnected or expired, tell the learner which one(s) to reconnect in "
        "the desktop app before making further calls.\n\n"
        "MANDATORY before calling add_entry, confirm all five: date (ISO "
        "YYYY-MM-DD), start time (HH:MM), duration (hours/minutes), activity "
        "type (id or exact name from list_activity_types), and a specific "
        "impact/reflection of at least 20 characters.\n\n"
        "PREVIEW BEFORE WRITING: show the learner the exact entry — date, start "
        "time, duration, activity type and the full impact/reflection text word "
        "for word — and wait for an explicit yes. Never hide, shorten or "
        "summarise the impact, and never call add_entry in the same turn as the "
        "first preview. If anything changes, show the revised preview again.\n\n"
        "ALWAYS ask follow-up questions about the activity type when it is "
        "missing or ambiguous (e.g. was it a live session, self-study, "
        "mentoring or learning by doing a work task?). Never guess the type, "
        "never invent details, and never log routine work or overtime as OTJ.\n\n"
        "Read the full skill with the `get_otj_guide` tool (or the log_otj "
        "prompt / timelog://otj-guide resource) before your first entry, and "
        "use `check_entry` to validate a draft and get the exact questions to "
        "ask the learner.\n\n"
        "TIMETABLED SESSIONS: when an entry comes from calendar_events or "
        "calendar_upcoming, ALWAYS read that week's QMplus material before "
        "writing the impact. Map the module code with qmplus_courses, find the "
        "week with qmplus_search or qmplus_course_contents, and read the slides "
        "or lab sheet with qmplus_fetch. Never write a reflection from the "
        "event title alone; if QMplus is unavailable, say so and ask the "
        "learner what was covered.\n\n"
        "Calendar tools: calendar_status, calendar_list, calendar_events and "
        "calendar_upcoming read the user's CampusM timetable. They use a "
        "separate session; if calendar_status says it is not connected, ask "
        "the user to open the desktop app and click Connect calendar.\n\n"
        "QMplus tools: qmplus_status, qmplus_courses, qmplus_course_contents, "
        "qmplus_search, qmplus_fetch and qmplus_current_lecture read the "
        "Moodle modules, files and slides. If they report authRequired, ask "
        "the user to connect QMplus in the app."
    ),
    version=APP_VERSION,
    debug=_DEBUG,
    log_level="DEBUG" if _DEBUG else "INFO",
)

_client: timelog.Timelog | None = None


def _tl() -> timelog.Timelog:
    global _client
    if _client is None:
        _client = timelog.Timelog()
    return _client


def _run(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    async def _inner() -> Any:
        return await anyio.to_thread.run_sync(lambda: fn(*args, **kwargs))

    return _inner()


def _fail(exc: Exception) -> Any:
    raise ValueError(f"{type(exc).__name__}: {exc}")


def _module_error(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, AuthRequired):
        return {"ok": False, "authRequired": True, "error": str(exc)}
    return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


@mcp.tool()
async def get_otj_guide() -> dict[str, str]:
    """Read the OTJ logging skill: what counts as off-the-job training, activity
    type guidance, reflection quality and the required follow-up questions."""
    return {"guide": OTJ_GUIDE}


@mcp.tool()
async def check_entry(
    date: str = "",
    start_time: str = "",
    hours: int = 0,
    minutes: int = 0,
    activity_type: str | int = "",
    impact: str = "",
) -> dict[str, Any]:
    """Validate a draft timelog entry before writing it.

    Returns {ready, issues, questions, activityTypeId, activityTypeName}.
    Call this whenever a detail is missing or the activity type is ambiguous,
    then ask the learner the returned questions.
    """
    return validate_entry(date, start_time, hours, minutes, activity_type, impact)


@mcp.prompt(
    title="Log off-the-job time",
    description=(
        "Guided OTJ logging: checks what counts, asks follow-up questions "
        "about activity type, duration and reflection, then writes the entry."
    ),
)
def log_otj(activity_type: str = "") -> str:
    hint = (
        f"The learner suggested activity type: {activity_type!r}. Confirm it."
        if activity_type
        else "No activity type has been chosen yet."
    )
    return f"""You are helping an apprentice log one off-the-job (OTJ) training entry.

{hint}

Collect these five things before calling add_entry:
1. date (YYYY-MM-DD)
2. start time (HH:MM, 24-hour)
3. duration (hours + minutes)
4. activity type (id or exact name)
5. a specific impact/reflection (20-2000 characters)

Rules:
- Ask 2-3 short follow-up questions at a time and offer options.
- ALWAYS clarify the activity type if it is missing or ambiguous. Ask whether
  it was a live session, self-study, mentoring/coaching, or learning by doing a
  work task, because that decides between types 13/1, 16, 17 and 19.
- If the activity sounds like routine work, overtime or unpaid time, challenge
  whether it is OTJ at all before logging it.
- If the activity is a timetabled session, read that week's QMplus slides or lab
  sheet before drafting the impact. Never write it from the event title alone.
- Never invent date, time, duration or reflection.
- Use check_entry to validate the draft.
- Once check_entry is ready, show a full preview before writing: date, start
  time, duration, activity type and the complete impact text word-for-word.
  Never replace the impact with a summary such as "impact added".
- After the preview, stop and wait for the learner's explicit yes. Never call
  add_entry in the same turn as the first preview. If anything changes, show
  the revised preview in full.
- After writing, confirm in one line: date, type, duration and entry id.

Full skill and definitions:

{OTJ_GUIDE}
"""


@mcp.resource(
    "timelog://otj-guide",
    name="otj-guide",
    title="Off-the-job logging guide",
    description="What counts as OTJ, activity type mapping and follow-up questions.",
    mime_type="text/markdown",
)
def otj_guide_resource() -> str:
    return OTJ_GUIDE


@mcp.tool()
async def ping() -> dict[str, bool]:
    """Health check. Returns {"pong": true} without touching the network."""
    return {"pong": True}


@mcp.tool()
async def auth_status() -> dict[str, Any]:
    tl_state = timelog.token_state()
    cal_state = ombiel_calendar.token_state()
    qm_state = qmplus_client.session_state()

    return {
        "ok": True,
        "checked_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "all_connected": bool(
            tl_state.get("connected")
            and cal_state.get("connected")
            and qm_state.get("connected")
        ),
        "timelog": tl_state,
        "calendar": cal_state,
        "qmplus": qm_state,
    }


@mcp.tool()
async def get_profile() -> dict[str, Any]:
    """Get the signed-in learner's profile (learner id, unit id, email, org)."""
    try:
        tl = _tl()
        profile = await _run(lambda: tl.profile)
        return {
            "learnerId": tl.learner_id,
            "unitId": await _run(lambda: tl.unit_id),
            "email": profile.get("email"),
            "organisation": profile.get("organisationName"),
        }
    except Exception as exc:
        _fail(exc)


@mcp.tool()
async def list_activity_types(include_inactive: bool = False) -> dict[str, Any]:
    """List activity types usable when logging time (id + text)."""
    try:
        items = await _run(_tl().activity_types, include_inactive)
        return {"activityTypes": items or []}
    except Exception as exc:
        _fail(exc)


@mcp.tool()
async def list_entries(from_date: str, to_date: str) -> dict[str, Any]:
    """List timelog entries between two ISO dates, e.g. 2026-09-01 and 2026-09-30."""
    try:
        items = await _run(_tl().list_entries, from_date, to_date) or []
        slim = [
            {
                "id": e.get("id"),
                "date": (e.get("startDateTime") or "")[:10],
                "start": e.get("activityStartTime"),
                "duration": e.get("timeSpent"),
                "activityType": e.get("activityType"),
                "impact": e.get("reflection"),
                "approved": e.get("approved"),
                "imported": e.get("isImported"),
            }
            for e in items
        ]
        return {"count": len(slim), "entries": slim}
    except Exception as exc:
        _fail(exc)


@mcp.tool()
async def add_entry(
    date: str,
    start_time: str,
    activity_type: str | int = "",
    impact: str = "",
    hours: int = 0,
    minutes: int = 0,
    unit_id: str | None = None,
) -> dict[str, Any]:
    """Log off-the-job time.

    Read get_otj_guide first and use check_entry if any detail is ambiguous.
    Anything missing or vague is returned as questions instead of writing.

    Args:
        date: ISO date, e.g. "2026-11-11".
        start_time: 24-hour start time, "HH:MM" (e.g. "09:00").
        activity_type: activity type id (e.g. 16) or exact name (e.g.
            "Electronic or distance learning, or self-study"). Use
            list_activity_types to discover valid values.
        impact: reflection on what was done and how it developed the learner.
            For timetabled sessions, read the matching QMplus material first.
        hours: whole hours of the activity (0-24).
        minutes: additional minutes (0-59).
        unit_id: optional unit id; defaults to the learner's main aim.
    """
    check = validate_entry(date, start_time, hours, minutes, activity_type, impact)
    if not check["ready"]:
        return {
            "ok": False,
            "ready": False,
            "issues": check["issues"],
            "questions": check["questions"],
            "hint": "Ask the learner these questions, then call add_entry again.",
        }

    try:
        new_id = await _run(
            _tl().add_entry,
            date,
            start_time,
            hours,
            minutes,
            check["activityTypeId"],
            impact,
            unit_id,
        )
        return {
            "ok": True,
            "id": new_id,
            "activityTypeId": check["activityTypeId"],
            "activityTypeName": check["activityTypeName"],
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


@mcp.tool()
async def delete_entry(entry_id: int) -> dict[str, Any]:
    """Delete a timelog entry by its numeric id (from list_entries)."""
    try:
        await _run(_tl().delete_entry, entry_id)
        return {"ok": True, "deleted": entry_id}
    except Exception as exc:
        _fail(exc)


@mcp.tool()
async def get_totals() -> Any:
    """Get the learner's off-the-job totals / progress summary."""
    try:
        tl = _tl()
        return await _run(
            lambda: tl._request(f"learner/{tl.learner_id}/off-the-job-totals")
        )
    except Exception as exc:
        _fail(exc)


@mcp.tool()
async def calendar_status() -> dict[str, Any]:
    """Check whether the CampusM calendar is connected and when its token expires."""
    try:
        return {"ok": True, **ombiel_calendar.token_state()}
    except Exception as exc:
        return _module_error(exc)


@mcp.tool()
async def calendar_list() -> dict[str, Any]:
    """List the user's CampusM calendars (e.g. Course Timetable)."""
    try:
        calendars = await _run(ombiel_calendar.CalendarClient().calendars)
        return {"ok": True, "count": len(calendars), "calendars": calendars}
    except Exception as exc:
        return _module_error(exc)


@mcp.tool()
async def calendar_events(
    calendar: str = "",
    from_date: str = "",
    to_date: str = "",
) -> dict[str, Any]:
    """List calendar events between two ISO dates (YYYY-MM-DD).

    Leave `calendar` empty to merge all calendars; use calendar_list for names.
    """
    try:
        today = dt.date.today()
        from_date = from_date or today.isoformat()
        to_date = to_date or (today + dt.timedelta(days=7)).isoformat()

        events = await _run(
            ombiel_calendar.CalendarClient().range_events,
            from_date,
            to_date,
            calendar or None,
        )
        return {
            "ok": True,
            "from": from_date,
            "to": to_date,
            "count": len(events),
            "events": events,
        }
    except Exception as exc:
        return _module_error(exc)


@mcp.tool()
async def calendar_upcoming(days: int = 7) -> dict[str, Any]:
    """Upcoming classes/events for the next N days (1-90)."""
    try:
        days = max(1, min(int(days), 90))
        events = await _run(ombiel_calendar.CalendarClient().upcoming, days)
        return {"ok": True, "days": days, "count": len(events), "events": events}
    except Exception as exc:
        return _module_error(exc)


@mcp.tool()
async def qmplus_status() -> dict[str, Any]:
    """Check whether QMplus is connected."""
    try:
        return {"ok": True, **qmplus_client.session_state()}
    except Exception as exc:
        return _module_error(exc)


@mcp.tool()
async def qmplus_courses() -> dict[str, Any]:
    """List the user's enrolled QMplus modules (course id, name, code)."""
    try:
        courses = await _run(qmplus_client.QmplusClient().courses)
        return {"ok": True, "count": len(courses), "courses": courses}
    except Exception as exc:
        return _module_error(exc)


@mcp.tool()
async def qmplus_course_contents(course_id: int) -> dict[str, Any]:
    """Get sections and activities for a QMplus module (compact list)."""
    try:
        contents = await _run(qmplus_client.QmplusClient().course_contents, course_id)
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
    except Exception as exc:
        return _module_error(exc)


@mcp.tool()
async def qmplus_search(course_id: int, query: str, deep: bool = False) -> dict[str, Any]:
    """Search a module's sections/activities/files. deep=True also searches PDF/PPTX text."""
    try:
        result = await _run(qmplus_client.QmplusClient().search, course_id, query, deep)
        return {"ok": True, **result}
    except Exception as exc:
        return _module_error(exc)


@mcp.tool()
async def qmplus_fetch(
    activity_url: str = "",
    course_id: int = 0,
    query: str = "",
) -> dict[str, Any]:
    """Fetch a module resource by URL, or by course_id + search query.

    Returns downloaded file text when possible (PDF/PPTX/TXT).
    """
    try:
        client = qmplus_client.QmplusClient()
        target = activity_url

        if not target and course_id and query:
            found = await _run(client.search, course_id, query, False)
            target = next(
                (item["url"] for item in found.get("results", []) if item.get("url")),
                "",
            )

        if not target:
            raise ValueError("Provide activity_url, or course_id + query")

        return await _run(client.fetch_url, target)
    except Exception as exc:
        return _module_error(exc)


@mcp.tool()
async def qmplus_current_lecture() -> dict[str, Any]:
    """Find the class in progress from the CampusM timetable and the matching QMplus module."""
    try:
        return await _run(qmplus_client.QmplusClient().current_lecture)
    except Exception as exc:
        return _module_error(exc)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Timelog MCP server")
    ap.add_argument("--transport", choices=["stdio", "http", "sse"], default="stdio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        tl = timelog.Timelog()
        print("profile:", json.dumps(tl.profile, indent=2))
        print("learnerId:", tl.learner_id, "unitId:", tl.unit_id)
        print(f"activity types: {len(tl.activity_types())}")

        entries = tl.list_entries("2026-09-01", "2026-11-11")
        print(f"entries: {len(entries)}")
        if entries:
            print("latest:", json.dumps(entries[0], indent=2)[:800])

        print("\nselftest OK")
        return 0

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        print(
            f"Timelog MCP listening on http://{args.host}:{args.port}/mcp",
            file=sys.stderr,
            flush=True,
        )
        mcp.run(transport="streamable-http", host=args.host, port=args.port)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        sys.exit(1)

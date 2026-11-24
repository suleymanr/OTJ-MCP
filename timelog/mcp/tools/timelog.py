from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from timelog.mcp.tools import call
from timelog.services import timelog as timelog_svc


def register(mcp: MCPServer, guide_text: str) -> None:
    @mcp.tool()
    async def get_otj_guide() -> dict[str, str]:
        """Read the OTJ logging guide: eligibility, activity types, reflection quality, and preview rules."""
        return {"guide": guide_text}

    @mcp.tool()
    async def check_entry(
        date: str = "",
        start_time: str = "",
        hours: int = 0,
        minutes: int = 0,
        activity_type: str | int = "",
        impact: str = "",
    ) -> dict[str, Any]:
        """Validate a draft timelog entry before writing it."""
        return timelog_svc.validate_entry(
            date, start_time, hours, minutes, activity_type, impact
        )

    @mcp.prompt(
        title="Log off-the-job time",
        description="Guided OTJ logging: checks eligibility, asks follow-ups, previews, then writes.",
    )
    def log_otj(activity_type: str = "") -> str:
        hint = (
            f"The learner suggested activity type: {activity_type!r}. Confirm it."
            if activity_type
            else "No activity type has been chosen yet."
        )
        return (
            f"Help an apprentice log one OTJ training entry. {hint}\n\n"
            "Follow the full guide below, validate with `check_entry`, and show the "
            "full word-for-word preview and wait for an explicit yes before calling `add_entry`.\n\n"
            f"{guide_text}"
        )

    @mcp.resource(
        "timelog://otj-guide",
        name="otj-guide",
        title="Off-the-job logging guide",
        description="What counts as OTJ, activity type mapping and follow-up questions.",
        mime_type="text/markdown",
    )
    def otj_guide_resource() -> str:
        return guide_text

    @mcp.tool()
    async def get_profile() -> dict[str, Any]:
        """Get the signed-in learner's profile (learner id, unit id, email, org)."""
        def _fetch() -> dict[str, Any]:
            tl = timelog_svc.TimelogClient()
            profile = tl.profile
            return {
                "learnerId": tl.learner_id,
                "unitId": tl.unit_id,
                "email": profile.get("email"),
                "organisation": profile.get("organisationName"),
            }

        return await call(_fetch)

    @mcp.tool()
    async def list_activity_types(include_inactive: bool = False) -> dict[str, Any]:
        """List activity types usable when logging time (id + text)."""
        return await call(
            lambda: {
                "activityTypes": timelog_svc.TimelogClient().activity_types(include_inactive)
            }
        )

    @mcp.tool()
    async def list_entries(from_date: str, to_date: str) -> dict[str, Any]:
        """List timelog entries between two ISO dates, e.g. 2026-09-01 and 2026-09-30."""
        def _fetch() -> dict[str, Any]:
            items = timelog_svc.TimelogClient().list_entries(from_date, to_date)
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

        return await call(_fetch)

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
        """Log off-the-job time after validating with check_entry and previewing."""
        check = timelog_svc.validate_entry(
            date, start_time, hours, minutes, activity_type, impact
        )
        if not check["ready"]:
            return {
                "ok": False,
                "ready": False,
                "issues": check["issues"],
                "questions": check["questions"],
                "hint": "Ask the learner these questions, then call add_entry again.",
            }

        return await call(
            lambda: {
                "ok": True,
                "id": timelog_svc.TimelogClient().add_entry(
                    date,
                    start_time,
                    hours,
                    minutes,
                    check["activityTypeId"],
                    impact,
                    unit_id,
                ),
                "activityTypeId": check["activityTypeId"],
                "activityTypeName": check["activityTypeName"],
            }
        )

    @mcp.tool()
    async def delete_entry(entry_id: int) -> dict[str, Any]:
        """Delete a timelog entry by its numeric id (from list_entries)."""
        return await call(
            lambda: (
                timelog_svc.TimelogClient().delete_entry(entry_id),
                {"ok": True, "deleted": entry_id},
            )[1]
        )

    @mcp.tool()
    async def get_totals() -> Any:
        """Get the learner's off-the-job totals / progress summary."""
        return await call(lambda: timelog_svc.TimelogClient().totals())

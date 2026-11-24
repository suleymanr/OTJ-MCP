from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import traceback
from typing import Any

from mcp.server.mcpserver import MCPServer

from timelog import paths
from timelog.config import (
    APP_VERSION,
    DEFAULT_PORT,
    MCP_HOST,
    MCP_SERVER_NAME,
    MCP_SERVER_TITLE,
)
from timelog.mcp.tools import register_all
from timelog.services import calendar as calendar_svc
from timelog.services import qmplus as qmplus_svc
from timelog.services import timelog as timelog_svc

_DEBUG = os.environ.get("TIMELOG_MCP_DEBUG") == "1"

try:
    OTJ_GUIDE = paths.GUIDE_FILE.read_text(encoding="utf-8")
except OSError:
    OTJ_GUIDE = (
        "Off-the-job (OTJ) training is learning during paid hours, outside "
        "normal duties, directly relevant to the apprenticeship standard. "
        "Ask for date, start time, duration, activity type and a specific "
        "reflection before logging."
    )

mcp = MCPServer(
    name=MCP_SERVER_NAME,
    title=MCP_SERVER_TITLE,
    instructions=(
        "Read and write off-the-job (OTJ) timelog entries on OneAdvanced Cloud "
        "Education, and inspect CampusM timetable and QMplus course materials.\n\n"
        "1. Call `auth_status` first if login states have not been checked in the "
        "last 15 minutes; if any required service is disconnected, tell the user "
        "which one(s) to reconnect in the desktop app.\n"
        "2. Read `get_otj_guide` (or `timelog://otj-guide`) before logging your "
        "first entry and follow its rules on eligibility, follow-up questions, "
        "QMplus lookup for timetabled sessions, and full word-for-word preview "
        "confirmation before calling `add_entry`.\n"
        "3. Use `check_entry` to validate drafts before writing."
    ),
    version=APP_VERSION,
    debug=_DEBUG,
    log_level="DEBUG" if _DEBUG else "INFO",
)


@mcp.tool()
async def ping() -> dict[str, bool]:
    """Health check. Returns {"pong": true} without touching the network."""
    return {"pong": True}


@mcp.tool()
async def auth_status() -> dict[str, Any]:
    """Check connection status for Timelog, Calendar, and QMplus."""
    tl_state = timelog_svc.token_state()
    cal_state = calendar_svc.token_state()
    qm_state = qmplus_svc.session_state()
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


register_all(mcp, OTJ_GUIDE)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Timelog MCP server")
    ap.add_argument("--transport", choices=["stdio", "http", "sse"], default="stdio")
    ap.add_argument("--host", default=MCP_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        tl = timelog_svc.TimelogClient()
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

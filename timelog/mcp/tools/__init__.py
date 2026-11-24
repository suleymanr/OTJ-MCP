from __future__ import annotations

from typing import Any, Callable

import anyio
from mcp.server.mcpserver import MCPServer

from timelog.core.http import AuthRequired, err_text


async def call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return await anyio.to_thread.run_sync(lambda: fn(*args, **kwargs))
    except AuthRequired as exc:
        return {"ok": False, "authRequired": True, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": err_text(exc)}


def register_all(mcp: MCPServer, guide_text: str) -> None:
    from timelog.mcp.tools import calendar, qmplus, timelog

    timelog.register(mcp, guide_text)
    calendar.register(mcp)
    qmplus.register(mcp)

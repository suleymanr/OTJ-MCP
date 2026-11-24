from __future__ import annotations

import os
from typing import Any

APP_NAME = "TimelogMCP"
APP_TITLE = "Timelog"
APP_VERSION = "1.0.0"

MCP_SERVER_NAME = "timelog"
MCP_SERVER_TITLE = "Cloud Education Timelog"
MCP_HOST = "127.0.0.1"
DEFAULT_PORT = int(os.environ.get("TIMELOG_MCP_PORT", "8765"))
KEEPALIVE_INTERVAL_S = 170

MAIN_WINDOW: dict[str, Any] = {
    "width": 700,
    "height": 640,
    "min_size": (500, 440),
    "bg": "#141416",
}

AUTH_WINDOW: dict[str, Any] = {
    "width": 560,
    "height": 560,
    "min_size": (460, 460),
}

AUTH_TIMEOUT_S = 1800
REFRESH_TIMEOUT_S = 20
POLL_INTERVAL_S = 1.5

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

HTTP_TIMEOUT_S = 60
CALENDAR_TIMEOUT_S = 45
TOKEN_TIMEOUT_S = 30
JWT_SKEW_S = 60
REFRESH_SKEW_S = 30

MAX_EXTRACTED_CHARS = 60_000
MAX_PAGE_CHARS = 20_000
DEEP_SEARCH_MAX_FILES = 12
FETCH_MAX_FILES = 8

REALM = "queen-mary-university-london"
CLIENT_ID = "advancedsso"
TOKEN_URL = (
    f"https://identity.oneadvanced.com/auth/realms/{REALM}"
    "/protocol/openid-connect/token"
)
API_ORIGIN = "https://education.oneadvanced.com"
API_BASE = f"{API_ORIGIN}/api/cloud-education/v1"
TIMELOG_START_URL = f"{API_ORIGIN}/cloud-education/timelog"

OMBIEL_BASE = "https://qmul.ombiel.co.uk"
OMBIEL_HOME = f"{OMBIEL_BASE}/campusm/home"
CALENDARS_PATH = "campusm/sso/calendars/CAL"
CAL2_PATH = "campusm/sso/cal2/"
OMBIEL_COOKIES = frozenset({"cmAuthToken", "a", "__a"})

QMPLUS_BASE = "https://qmplus.qmul.ac.uk"
QMPLUS_HOME = f"{QMPLUS_BASE}/my/"
QMPLUS_LOGIN = f"{QMPLUS_BASE}/login/index.php"
QMPLUS_COOKIES = frozenset(
    {"MoodleSession", "MDL_SSP_AuthToken", "MDL_SSP_SessID", "MOODLEID1_"}
)

AUTH_SERVICES: dict[str, tuple[str, str]] = {
    "timelog": ("Sign in — OneAdvanced", TIMELOG_START_URL),
    "calendar": ("Sign in — CampusM", OMBIEL_HOME),
    "qmplus": ("Sign in — QMplus", QMPLUS_LOGIN),
}

ACTIVITY_TYPES: dict[int, str] = {
    1: "Virtual Training Session",
    13: "Traditional face-to-face session",
    15: "Trainer or assessor led training",
    16: "Electronic or distance learning, or self-study",
    17: "Coaching or mentoring",
    18: "Guided learning with no trainer/assessor present",
    19: "Gaining technical experience by doing my job",
    20: "Review/feedback/support",
    22: "Other",
    23: "Furloughed",
}

TYPE_BY_NAME: dict[str, int] = {
    name.lower(): tid for tid, name in ACTIVITY_TYPES.items()
}

MCP_TOOL_NAMES: tuple[str, ...] = (
    "auth_status",
    "get_profile",
    "list_activity_types",
    "list_entries",
    "add_entry",
    "delete_entry",
    "get_totals",
    "get_otj_guide",
    "check_entry",
    "calendar_status",
    "calendar_list",
    "calendar_events",
    "calendar_upcoming",
    "qmplus_status",
    "qmplus_courses",
    "qmplus_course_contents",
    "qmplus_search",
    "qmplus_fetch",
    "qmplus_current_lecture",
    "ping",
)

MCP_CLIENTS: dict[str, dict[str, Any]] = {
    "claude-code": {
        "name": "Claude Code",
        "key": "mcpServers",
        "root": "home",
        "rel_path": (".claude.json",),
        "bins": ("claude",),
        "detect_dirs": (("home", (".claude",)),),
        "detect_file": True,
        "supports_http": True,
        "note": "User-scope MCP servers in ~/.claude.json",
    },
    "claude-desktop": {
        "name": "Claude Desktop",
        "key": "mcpServers",
        "root": "appdata",
        "rel_path": ("Claude", "claude_desktop_config.json"),
        "bins": (),
        "detect_dirs": (("appdata", ("Claude",)),),
        "detect_file": False,
        "supports_http": False,
        "note": "Requires restarting Claude Desktop",
    },
    "antigravity": {
        "name": "Antigravity",
        "key": "mcpServers",
        "root": "home",
        "rel_path": (".gemini", "config", "mcp_config.json"),
        "bins": ("agy", "antigravity"),
        "detect_dirs": (
            ("home", (".gemini", "antigravity-cli")),
            ("home", (".gemini", "antigravity")),
        ),
        "detect_file": True,
        "supports_http": True,
        "note": "~/.gemini/config/mcp_config.json",
    },
    "gemini": {
        "name": "Gemini CLI",
        "key": "mcpServers",
        "root": "home",
        "rel_path": (".gemini", "settings.json"),
        "bins": ("gemini",),
        "detect_dirs": (("home", (".gemini",)),),
        "detect_file": False,
        "supports_http": True,
        "note": "~/.gemini/settings.json",
    },
    "codex": {
        "name": "Codex CLI",
        "key": "mcp_servers",
        "root": "home",
        "rel_path": (".codex", "config.toml"),
        "bins": ("codex",),
        "detect_dirs": (("home", (".codex",)),),
        "detect_file": False,
        "supports_http": True,
        "note": "~/.codex/config.toml",
    },
    "cursor": {
        "name": "Cursor",
        "key": "mcpServers",
        "root": "home",
        "rel_path": (".cursor", "mcp.json"),
        "bins": ("cursor",),
        "detect_dirs": (("home", (".cursor",)),),
        "detect_file": False,
        "supports_http": True,
        "note": "Global MCP config for Cursor",
    },
    "windsurf": {
        "name": "Windsurf",
        "key": "mcpServers",
        "root": "home",
        "rel_path": (".codeium", "windsurf", "mcp_config.json"),
        "bins": ("windsurf",),
        "detect_dirs": (("home", (".codeium",)),),
        "detect_file": False,
        "supports_http": True,
        "note": "mcp_config.json for Windsurf",
    },
    "vscode": {
        "name": "VS Code (Copilot MCP)",
        "key": "servers",
        "root": "appdata",
        "rel_path": ("Code", "User", "mcp.json"),
        "bins": ("code",),
        "detect_dirs": (("appdata", ("Code",)),),
        "detect_file": False,
        "supports_http": True,
        "note": "User-level mcp.json",
    },
    "zed": {
        "name": "Zed",
        "key": "context_servers",
        "root": "zed",
        "rel_path": ("settings.json",),
        "bins": ("zed",),
        "detect_dirs": (("zed", ()),),
        "detect_file": False,
        "supports_http": False,
        "note": "context_servers in Zed settings",
    },
}


def mcp_http_url(port: int = DEFAULT_PORT) -> str:
    return f"http://{MCP_HOST}:{port}/mcp"

from __future__ import annotations

import os

APP_NAME = "TimelogMCP"
APP_VERSION = "1.0.0"
EXE_NAME = "timelog-mcp.exe"
GITHUB_REPO = os.environ.get("TIMELOG_GITHUB_REPO", "")

DEFAULT_PORT = 8765
WINDOW_SIZE = 560

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

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

QMPLUS_BASE = "https://qmplus.qmul.ac.uk"
QMPLUS_HOME = f"{QMPLUS_BASE}/my/"
QMPLUS_LOGIN = f"{QMPLUS_BASE}/login/index.php"

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

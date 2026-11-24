<h1 align="center">
  <img src="timelog/desktop/ui/icons/timelog.ico" width="32" align="absmiddle" alt="TimelogMCP" />
  TimelogMCP
</h1>

<p align="center">
Desktop app and MCP for logging OTJ training & allowing agents to interact with lecture material or documents
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey" />
</p>

| | Connection | Tools |
| :---: | :--- | :--- |
| <img src="timelog/desktop/ui/icons/education.png" width="24" alt="OneAdvanced"> | **OneAdvanced** | `auth_status`, `open_login`, `get_profile`, `list_activity_types`, `list_entries`, `add_entry`, `delete_entry`, `get_totals`, `check_entry`, `get_otj_guide`, `ping` |
| <img src="timelog/desktop/ui/icons/timetable.png" width="24" alt="Ombiel"> | **Ombiel (Timetable)** | `calendar_status`, `calendar_list`, `calendar_events`, `calendar_upcoming` |
| <img src="timelog/desktop/ui/icons/materials.png" width="24" alt="QMplus"> | **QMplus** | `qmplus_status`, `qmplus_courses`, `qmplus_course_contents`, `qmplus_search`, `qmplus_fetch`, `qmplus_current_lecture` |

---

## Installation

1. Download the release zip for your OS from **Releases** and extract `timelog-mcp` anywhere:
   - **Windows:** `TimelogMCP-windows.zip`: double-click `mcp.lnk`
   - **macOS:** `TimelogMCP-macos.zip`: double-click `TimelogMCP.app`
2. Requires **Python 3.11+**.

On launch, `launch.py` checks for updates via Git (installing Git if missing), sets up `.venv`, installs dependencies, and opens TimelogMCP.

---

## Data & Credentials

Session tokens and browser profiles are stored locally outside the repository:

- **Windows:** `%LOCALAPPDATA%\TimelogMCP`
- **macOS:** `~/Library/Application Support/TimelogMCP`
- **Linux:** `~/.local/share/TimelogMCP`

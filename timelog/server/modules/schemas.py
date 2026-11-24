from __future__ import annotations

from typing import Any

from timelog.config import ACTIVITY_TYPES, TYPE_BY_NAME


class ModuleError(RuntimeError):
    pass


class AuthRequired(ModuleError):
    pass


class CalendarAuthRequired(AuthRequired):
    pass


class CalendarError(ModuleError):
    pass


class QmplusAuthRequired(AuthRequired):
    pass


class QmplusError(ModuleError):
    pass


def resolve_activity_type(activity_type: str | int | None) -> tuple[int | None, str | None]:
    if activity_type is None:
        return None, None

    raw = str(activity_type).strip()
    if not raw:
        return None, None

    if raw.isdigit():
        tid = int(raw)
        if tid in ACTIVITY_TYPES:
            return tid, ACTIVITY_TYPES[tid]
        return None, None

    tid = TYPE_BY_NAME.get(raw.lower())
    if tid is not None:
        return tid, ACTIVITY_TYPES[tid]

    return None, None


def validate_entry(
    date: str,
    start_time: str,
    hours: int,
    minutes: int,
    activity_type: str | int,
    impact: str,
) -> dict[str, Any]:
    issues: list[str] = []
    questions: list[str] = []

    if not (date or "").strip():
        issues.append("date is missing")
        questions.append("What date was the activity? (YYYY-MM-DD)")

    if not (start_time or "").strip():
        issues.append("start time is missing")
        questions.append("What time did it start? (HH:MM, 24-hour)")

    try:
        h, m = int(hours or 0), int(minutes or 0)
    except (TypeError, ValueError):
        h = m = 0

    if h <= 0 and m <= 0:
        issues.append("duration is missing or zero")
        questions.append("How long did it last? (hours and minutes)")

    tid, name = resolve_activity_type(activity_type)
    if tid is None:
        if activity_type in (None, ""):
            issues.append("activity type is missing")
        else:
            issues.append(f"unknown activity type: {activity_type!r}")
        questions.append(
            "Which activity type fits best: 13 face-to-face, 1 virtual, "
            "16 self-study, 17 mentoring/coaching, 19 learning by doing your "
            "job, 20 review/feedback, 22 other?"
        )
    elif tid == 23:
        issues.append("Furloughed is not off-the-job training")
        questions.append(
            "What learning did you do during paid hours that relates to your standard?"
        )

    text = (impact or "").strip()
    if not text:
        issues.append("impact/reflection is missing")
        questions.append(
            "What did you learn, and how does it link to your standard or KSBs?"
        )
    elif len(text) < 20:
        issues.append("impact/reflection is too short (minimum 20 characters)")
        questions.append(
            "Can you add a sentence on what you learned and how you will use it?"
        )

    return {
        "ready": not issues,
        "issues": issues,
        "questions": questions,
        "activityTypeId": tid,
        "activityTypeName": name,
    }

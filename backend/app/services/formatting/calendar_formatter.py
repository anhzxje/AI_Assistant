"""Safe user-facing Calendar event formatting."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


EMAIL_LIKE_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
BRACKETED_RE = re.compile(r"\s*\[([^\]]+)\]\s*")


def format_calendar_event_for_user(event: dict[str, Any], role: str = "user") -> str:
    """Format a Calendar event without leaking calendar IDs or source IDs."""

    title = clean_event_title(str(event.get("summary") or "Sự kiện không có tiêu đề"))
    when = format_event_time(event)
    location = clean_text(str(event.get("location") or ""))
    calendar_name = friendly_calendar_name(event, role=role)

    details = title
    if location:
        details = f"{details}, {location}"
    if calendar_name:
        details = f"{details} ({calendar_name})"
    return f"{when} — {details}"


def clean_event_title(title: str) -> str:
    def replace_bracket(match: re.Match[str]) -> str:
        content = match.group(1)
        return " " if is_ugly_identifier(content) else f" [{content}] "

    title = BRACKETED_RE.sub(replace_bracket, title)
    title = EMAIL_LIKE_RE.sub("", title)
    return clean_text(title) or "Sự kiện không có tiêu đề"


def friendly_calendar_name(event: dict[str, Any], role: str = "user") -> str:
    name = clean_text(str(event.get("calendar_name") or ""))
    if not name:
        return ""
    if role != "admin" and is_ugly_identifier(name):
        return ""
    return name


def format_event_time(event: dict[str, Any]) -> str:
    date_text = str(event.get("start_date") or "")
    time_text = str(event.get("start_time") or "")
    formatted_date = format_date(date_text)
    if event.get("is_all_day"):
        return f"{formatted_date} Cả ngày".strip()
    if time_text:
        return f"{formatted_date} {time_text[:5]}".strip()
    return formatted_date or "Không rõ thời gian"


def format_date(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return value


def clean_text(value: str) -> str:
    return " ".join(value.replace("\n", " ").split()).strip(" ,;-")


def is_ugly_identifier(value: str) -> bool:
    text = value.strip().lower()
    if not text:
        return False
    if EMAIL_LIKE_RE.search(text):
        return True
    ugly_fragments = (
        "calendar.google.com",
        "group.v.calendar",
        "import.calendar",
        "#holiday",
        "resource.calendar",
    )
    if any(fragment in text for fragment in ugly_fragments):
        return True
    if re.fullmatch(r"[a-z0-9._%+-]{8,}", text) and not re.search(r"\s", text):
        return True
    return False

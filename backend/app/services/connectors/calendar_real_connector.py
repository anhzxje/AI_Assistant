"""Real Google Calendar read-only adapter."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from backend.app.services.integrations.google_token_store import GoogleTokenStore


READABLE_ROLES = {"reader", "writer", "owner"}


def list_calendar_readonly(
    user_id: str,
    token_store: GoogleTokenStore | None = None,
) -> list[dict[str, Any]]:
    service = build_calendar_service(user_id, token_store)
    payload = service.calendarList().list(showHidden=True, minAccessRole="reader").execute()
    calendars = [normalize_calendar_list_item(item) for item in payload.get("items", [])]
    calendars.sort(key=lambda item: (not item.get("primary", False), not item.get("selected", False), str(item.get("summary") or "").lower()))
    return calendars


def sync_calendar_readonly(
    user_id: str,
    days_ahead: int = 7,
    token_store: GoogleTokenStore | None = None,
    include_cancelled: bool = False,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    calendar_ids: list[str] | None = None,
    include_all_calendars: bool = False,
    include_holidays: bool = False,
) -> dict[str, Any] | list[dict[str, Any]]:
    service = build_calendar_service(user_id, token_store)
    available = [normalize_calendar_list_item(item) for item in service.calendarList().list(showHidden=True, minAccessRole="reader").execute().get("items", [])]
    selected = select_calendars(
        available,
        calendar_ids=calendar_ids,
        include_all_calendars=include_all_calendars,
        include_holidays=include_holidays,
    )
    range_start, range_end = resolve_date_range(start_date=start_date, end_date=end_date, days_ahead=days_ahead)
    events: list[dict[str, Any]] = []
    for calendar in selected:
        time_min, time_max = rfc3339_bounds(range_start, range_end, calendar.get("timeZone"))
        payload = service.events().list(
            calendarId=calendar["id"],
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            showDeleted=include_cancelled,
        ).execute()
        for item in payload.get("items", []):
            if not include_cancelled and item.get("status") == "cancelled":
                continue
            events.append(normalize_calendar_api_event(item, calendar=calendar))

    return {
        "events": events,
        "calendars": selected,
        "available_calendars": available,
        "date_range": {"start_date": range_start.isoformat(), "end_date": range_end.isoformat()},
    }


def build_calendar_service(user_id: str, token_store: GoogleTokenStore | None = None):
    store = token_store or GoogleTokenStore()
    token = store.refresh_if_needed(user_id, "calendar")
    if not token or not token.get("access_token"):
        raise RuntimeError("calendar_not_connected")

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except Exception as exc:
        raise RuntimeError("google_libraries_unavailable") from exc

    credentials = Credentials(token=token["access_token"])
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def normalize_calendar_list_item(item: dict[str, Any]) -> dict[str, Any]:
    summary = item.get("summary") or item.get("id") or ""
    calendar_id = item.get("id") or ""
    return {
        "id": calendar_id,
        "summary": summary,
        "description": item.get("description") or "",
        "primary": bool(item.get("primary")),
        "selected": bool(item.get("selected")) or bool(item.get("primary")),
        "accessRole": item.get("accessRole") or "",
        "backgroundColor": item.get("backgroundColor") or "",
        "timeZone": item.get("timeZone") or "",
        "is_holiday": is_holiday_calendar(summary, calendar_id),
        "is_classroom": is_classroom_calendar(summary, calendar_id),
    }


def select_calendars(
    calendars: list[dict[str, Any]],
    *,
    calendar_ids: list[str] | None,
    include_all_calendars: bool,
    include_holidays: bool,
) -> list[dict[str, Any]]:
    wanted_ids = {str(item) for item in calendar_ids or [] if str(item).strip()}
    selected: list[dict[str, Any]] = []
    for calendar in calendars:
        if calendar.get("accessRole") not in READABLE_ROLES:
            continue
        if calendar.get("is_holiday") and not include_holidays:
            continue
        if wanted_ids:
            include = str(calendar.get("id")) in wanted_ids
        elif include_all_calendars:
            include = True
        else:
            include = bool(calendar.get("primary")) or bool(calendar.get("selected"))
        if include:
            selected.append(calendar)
    return selected


def resolve_date_range(
    *,
    start_date: date | str | None,
    end_date: date | str | None,
    days_ahead: int,
) -> tuple[date, date]:
    start = parse_date(start_date) if start_date else date.today()
    end = parse_date(end_date) if end_date else start + timedelta(days=min(max(0, days_ahead), 365))
    if end < start:
        raise ValueError("calendar_date_range_invalid")
    if (end - start).days > 365:
        raise ValueError("calendar_date_range_too_large")
    return start, end


def rfc3339_bounds(start: date, end: date, timezone_name: str | None) -> tuple[str, str]:
    tz = local_timezone(timezone_name)
    start_dt = datetime.combine(start, time.min, tzinfo=tz)
    end_exclusive = datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz)
    return start_dt.isoformat(), end_exclusive.isoformat()


def local_timezone(timezone_name: str | None):
    if timezone_name:
        try:
            return ZoneInfo(timezone_name)
        except Exception:
            pass
    return datetime.now().astimezone().tzinfo or timezone.utc


def parse_date(value: date | str | None) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value or date.today().isoformat()))


def normalize_calendar_api_event(event: dict[str, Any], *, calendar: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = event.get("summary") or ""
    description = event.get("description") or ""
    start = event.get("start") or {}
    end = event.get("end") or {}
    is_all_day = bool(start.get("date") and not start.get("dateTime"))
    return {
        "id": event.get("id"),
        "calendar_id": calendar.get("id") if calendar else event.get("calendar_id", "primary"),
        "calendar_name": calendar.get("summary") if calendar else event.get("calendar_name", "Primary"),
        "summary": summary,
        "description": description,
        "start": start,
        "end": end,
        "is_all_day": is_all_day,
        "location": event.get("location") or "",
        "htmlLink": event.get("htmlLink") or "",
        "attendees": [
            {"email": attendee.get("email"), "responseStatus": attendee.get("responseStatus")}
            for attendee in event.get("attendees") or []
        ],
        "status": event.get("status") or "confirmed",
        "category": classify_event(summary, description, is_holiday=bool(calendar and calendar.get("is_holiday"))),
        "priority_hint": priority_hint(summary, description, is_holiday=bool(calendar and calendar.get("is_holiday"))),
        "source_mode": "real",
    }


def is_holiday_calendar(summary: str, calendar_id: str = "") -> bool:
    text = f"{summary} {calendar_id}".lower()
    return any(term in text for term in ("holiday", "ngày lễ", "holidays", "lễ"))


def is_classroom_calendar(summary: str, calendar_id: str = "") -> bool:
    text = f"{summary} {calendar_id}".lower()
    return any(term in text for term in ("classroom", "class", "lớp", "course"))


def classify_event(summary: str, description: str, *, is_holiday: bool = False) -> str:
    if is_holiday:
        return "holiday"
    text = f"{summary} {description}".lower()
    if any(term in text for term in ("exam", "thi", "kiá»ƒm tra")):
        return "exam"
    if any(term in text for term in ("deadline", "háº¡n ná»™p")):
        return "deadline"
    if any(term in text for term in ("seminar", "workshop")):
        return "seminar"
    if any(term in text for term in ("meeting", "há»p")):
        return "meeting"
    if any(term in text for term in ("class", "lá»›p", "mÃ´n")):
        return "class"
    return "personal"


def priority_hint(summary: str, description: str, *, is_holiday: bool = False) -> str:
    if is_holiday:
        return "low"
    text = f"{summary} {description}".lower()
    if any(term in text for term in ("exam", "thi", "deadline", "háº¡n ná»™p", "urgent")):
        return "high"
    if any(term in text for term in ("meeting", "há»p", "seminar")):
        return "medium"
    return "low"

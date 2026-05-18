"""Calendar today node."""

from __future__ import annotations

from datetime import date, timedelta

from backend.app.api.google import get_personal_ingestion_service
from backend.app.services.context.context_engine import ContextEngine
from backend.app.services.connectors.personal_ingestion import read_jsonl
from backend.app.config import get_backend_settings
from backend.app.services.formatting.calendar_formatter import format_calendar_event_for_user
from orchestration.assistant_brain import normalize_text


def run(state: dict) -> dict:
    service = get_personal_ingestion_service()
    start_date, end_date, label = requested_calendar_window(state.get("message", ""))
    stats = service.sync_calendar(
        user_id=state["user_id"],
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        days_ahead=(end_date - start_date).days,
        include_all_calendars=True,
        include_holidays=False,
        use_mock=state.get("use_mock_google", False),
    )
    if not stats.connected:
        state["answer"] = "Calendar chưa được kết nối. Bạn có thể kết nối Calendar trong Cài đặt hoặc bật dữ liệu mẫu để demo."
        state["sources"] = [{"type": "calendar", "source_mode": "not_connected"}]
        state["actions"] = ["calendar_not_connected"]
        state["metadata"]["google"] = {
            "source_mode": "not_connected",
            "calendar_connected": False,
            "event_count": 0,
            "today_count": 0,
        }
        state["memory_used"] = False
        return state
    today = service.today_calendar(user_id=state["user_id"])
    context = ContextEngine().build(user_id=state["user_id"])
    events = calendar_events_for_window(state["user_id"], start_date=start_date, end_date=end_date)
    if not events:
        answer = f"Không có sự kiện Calendar nào trong {label}."
    else:
        lines = [f"Lịch trong {label}:"]
        for event in events:
            lines.append(f"- {format_calendar_event_for_user(event, role=str(state.get('auth_role') or 'user'))}")
        answer = "\n".join(lines)
    state["answer"] = answer
    state["sources"] = [
        {"type": "calendar", "event_id": item.get("event_id"), "summary": item.get("summary"), "calendar_name": item.get("calendar_name")}
        for item in events
    ] or [{"type": "calendar", "date_range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}, "events": 0}]
    state["actions"] = ["calendar_readonly_sync", "calendar_mock_sync" if state.get("use_mock_google", False) else "calendar_real_sync"]
    state["metadata"]["google"] = {
        "source_mode": stats.source_mode if stats.connected else "not_connected",
        "calendar_connected": stats.connected and stats.source_mode == "real",
        "event_count": len(events),
        "today_count": len(today.get("events", [])),
        "date_range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        "context_meetings": len(context.meetings),
    }
    state["memory_used"] = False
    return state


def requested_calendar_window(message: str) -> tuple[date, date, str]:
    text = normalize_text(message or "")
    today = date.today()
    if "ngay mai" in text or "tomorrow" in text:
        target = today + timedelta(days=1)
        return target, target, "ngày mai"
    if "tuan" in text or "week" in text:
        return today, today + timedelta(days=7), "7 ngày tới"
    if "thang" in text or "month" in text:
        return today, today + timedelta(days=31), "tháng này"
    return today, today, "hôm nay"


def calendar_events_for_window(user_id: str, *, start_date: date, end_date: date) -> list[dict]:
    data_root = get_backend_settings().data_settings.resolved_data_root
    items = []
    for item in read_jsonl(data_root / "processed" / "personal" / "calendar_events.jsonl"):
        if item.get("user_id") != user_id or not item.get("start_date"):
            continue
        try:
            item_date = date.fromisoformat(str(item.get("start_date")))
        except ValueError:
            continue
        if start_date <= item_date <= end_date:
            items.append(item)
    return sorted(items, key=lambda item: (item.get("start_date") or "", item.get("start_time") or ""))

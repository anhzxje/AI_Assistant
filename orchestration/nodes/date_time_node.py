"""Local date and time utility node."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from orchestration.assistant_brain import normalize_text


WEEKDAYS_VI = [
    "thứ Hai",
    "thứ Ba",
    "thứ Tư",
    "thứ Năm",
    "thứ Sáu",
    "thứ Bảy",
    "Chủ nhật",
]


def run(state: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now().astimezone()
    text = normalize_text(state.get("message", ""))

    if "ngay mai" in text:
        target = now + timedelta(days=1)
        answer = format_date_answer("Ngày mai", target)
    elif "hom qua" in text:
        target = now - timedelta(days=1)
        answer = format_date_answer("Hôm qua", target)
    elif "may gio" in text or "thoi gian" in text or "bay gio" in text:
        answer = f"Bây giờ là {now:%H:%M}, {WEEKDAYS_VI[now.weekday()]}, ngày {now:%d/%m/%Y}."
    else:
        answer = format_date_answer("Hôm nay", now)

    state["answer"] = answer
    state["sources"] = []
    state["actions"] = ["date_time_local"]
    state["memory_used"] = False
    state["metadata"]["general_llm_mode"] = "not_used"
    state["metadata"]["date_time"] = {
        "timezone": str(now.tzinfo),
        "iso": now.isoformat(),
    }
    return state


def format_date_answer(label: str, value: datetime) -> str:
    return f"{label} là {WEEKDAYS_VI[value.weekday()]}, ngày {value:%d/%m/%Y}."

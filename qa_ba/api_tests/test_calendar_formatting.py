from __future__ import annotations

from backend.app.services.formatting.calendar_formatter import format_calendar_event_for_user


def test_calendar_answer_hides_email_like_calendar_id() -> None:
    event = {
        "summary": "Lịch thi Khai phá dữ liệu [23001857@hus.edu.vn]",
        "start_date": "2026-05-20",
        "start_time": "08:00:00",
        "location": "Phòng 201",
        "calendar_name": "23001857@hus.edu.vn",
    }

    text = format_calendar_event_for_user(event)

    assert "23001857@hus.edu.vn" not in text
    assert "20/05/2026 08:00" in text
    assert "Lịch thi Khai phá dữ liệu" in text
    assert "Phòng 201" in text


def test_calendar_answer_formats_all_day_event() -> None:
    event = {
        "summary": "Deadline báo cáo",
        "start_date": "2026-05-23",
        "is_all_day": True,
        "calendar_name": "Lớp Data Mining",
    }

    text = format_calendar_event_for_user(event)

    assert text.startswith("23/05/2026 Cả ngày")
    assert "Deadline báo cáo" in text
    assert "Lớp Data Mining" in text

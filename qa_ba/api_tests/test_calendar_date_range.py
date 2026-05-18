from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from backend.app.main import app
from qa_ba.api_tests.auth_helpers import user_headers
from qa_ba.api_tests.test_calendar_multi_calendar_sync import FakeCalendarService, install_fake_calendar
from orchestration.nodes.calendar_node import requested_calendar_window


def test_exact_start_end_dates_map_to_calendar_time_bounds(monkeypatch) -> None:
    start = date.today()
    end = start + timedelta(days=30)
    calendars = [
        {"id": "primary", "summary": "Primary", "primary": True, "selected": True, "accessRole": "owner", "timeZone": "Asia/Bangkok"}
    ]
    service = FakeCalendarService(calendars, {"primary": []})
    install_fake_calendar(monkeypatch, service)
    client = TestClient(app)

    response = client.post(
        "/api/google/calendar/sync",
        headers=user_headers(client),
        json={
            "use_mock": False,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "calendar_ids": ["primary"],
        },
    )

    assert response.status_code == 200
    assert response.json()["date_range"] == {"start_date": start.isoformat(), "end_date": end.isoformat()}
    assert service.event_calls[0]["timeMin"].startswith(f"{start.isoformat()}T00:00:00")
    assert service.event_calls[0]["timeMax"].startswith(f"{(end + timedelta(days=1)).isoformat()}T00:00:00")


def test_invalid_calendar_date_range_returns_422() -> None:
    client = TestClient(app)
    headers = user_headers(client)

    response = client.post(
        "/api/google/calendar/sync",
        headers=headers,
        json={"use_mock": False, "start_date": "2026-06-01", "end_date": "2026-05-01"},
    )
    too_large = client.post(
        "/api/google/calendar/sync",
        headers=headers,
        json={"use_mock": False, "start_date": "2026-01-01", "end_date": "2027-01-02"},
    )
    partial = client.post(
        "/api/google/calendar/sync",
        headers=headers,
        json={"use_mock": False, "start_date": "2026-01-01"},
    )

    assert response.status_code == 422
    assert too_large.status_code == 422
    assert partial.status_code == 422


def test_briefing_uses_synced_selected_calendar_events(monkeypatch) -> None:
    today = date.today()
    calendars = [
        {"id": "classroom-1", "summary": "Classroom Data Mining", "selected": True, "accessRole": "reader", "timeZone": "Asia/Bangkok"}
    ]
    events = {
        "classroom-1": [
            {
                "id": "c-today",
                "summary": "Classroom lab review",
                "start": {"dateTime": f"{today.isoformat()}T13:30:00+07:00"},
                "end": {"dateTime": f"{today.isoformat()}T14:30:00+07:00"},
                "status": "confirmed",
            }
        ]
    }
    install_fake_calendar(monkeypatch, FakeCalendarService(calendars, events))
    client = TestClient(app)
    headers = user_headers(client)

    sync_response = client.post(
        "/api/google/calendar/sync",
        headers=headers,
        json={"use_mock": False, "calendar_ids": ["classroom-1"], "start_date": today.isoformat(), "end_date": today.isoformat()},
    )
    briefing = client.get("/api/assistant/daily-briefing", headers=headers)

    assert sync_response.status_code == 200
    assert briefing.status_code == 200
    today_events = briefing.json()["today_events"]
    assert any(event["summary"] == "Classroom lab review" for event in today_events)
    assert any(event["calendar_name"] == "Classroom Data Mining" for event in today_events)


def test_empty_calendar_sync_returns_zero_counts_and_frontend_empty_message(monkeypatch) -> None:
    calendars = [
        {"id": "primary", "summary": "Primary", "primary": True, "selected": True, "accessRole": "owner", "timeZone": "Asia/Bangkok"}
    ]
    install_fake_calendar(monkeypatch, FakeCalendarService(calendars, {"primary": []}))
    client = TestClient(app)

    response = client.post(
        "/api/google/calendar/sync",
        headers=user_headers(client),
        json={"use_mock": False, "calendar_ids": ["primary"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["events_count"] == 0
    assert body["events"] == []

    calendar_panel = "frontend/components/briefing/CalendarPanel.tsx"
    assert "Không có sự kiện nào trong khoảng ngày đã chọn" in open(calendar_panel, encoding="utf-8").read()


def test_calendar_query_window_understands_vietnamese_week_and_month() -> None:
    today = date.today()

    week_start, week_end, week_label = requested_calendar_window("tuần này tôi có lịch gì")
    month_start, month_end, month_label = requested_calendar_window("tôi có sự kiện nào trong tháng này")
    tomorrow_start, tomorrow_end, tomorrow_label = requested_calendar_window("ngày mai tôi có lịch gì")

    assert (week_start, week_end, week_label) == (today, today + timedelta(days=7), "7 ngày tới")
    assert (month_start, month_end, month_label) == (today, today + timedelta(days=31), "tháng này")
    assert (tomorrow_start, tomorrow_end, tomorrow_label) == (today + timedelta(days=1), today + timedelta(days=1), "ngày mai")

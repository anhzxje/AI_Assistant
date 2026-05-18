from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi.testclient import TestClient

from backend.app.main import app
from qa_ba.api_tests.auth_helpers import user_headers


class FakeRequest:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def execute(self) -> dict[str, Any]:
        return self.payload


class FakeCalendarList:
    def __init__(self, calendars: list[dict[str, Any]]) -> None:
        self.calendars = calendars

    def list(self, **kwargs) -> FakeRequest:
        return FakeRequest({"items": self.calendars})


class FakeEvents:
    def __init__(self, service: "FakeCalendarService") -> None:
        self.service = service

    def list(self, **kwargs) -> FakeRequest:
        self.service.event_calls.append(kwargs)
        return FakeRequest({"items": self.service.events_by_calendar.get(kwargs["calendarId"], [])})


class FakeCalendarService:
    def __init__(self, calendars: list[dict[str, Any]], events_by_calendar: dict[str, list[dict[str, Any]]]) -> None:
        self.calendars = calendars
        self.events_by_calendar = events_by_calendar
        self.event_calls: list[dict[str, Any]] = []

    def calendarList(self) -> FakeCalendarList:
        return FakeCalendarList(self.calendars)

    def events(self) -> FakeEvents:
        return FakeEvents(self)


def calendar_fixture() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    today = date.today()
    calendars = [
        {"id": "primary", "summary": "Primary", "primary": True, "selected": True, "accessRole": "owner", "timeZone": "Asia/Bangkok"},
        {"id": "classroom-1", "summary": "Classroom Data Mining", "selected": True, "accessRole": "reader", "timeZone": "Asia/Bangkok"},
        {"id": "holiday-vn", "summary": "Vietnam Holidays", "selected": True, "accessRole": "reader", "timeZone": "Asia/Bangkok"},
    ]
    events = {
        "primary": [
            {
                "id": "p1",
                "summary": "Primary meeting",
                "start": {"dateTime": f"{today.isoformat()}T09:00:00+07:00"},
                "end": {"dateTime": f"{today.isoformat()}T10:00:00+07:00"},
                "status": "confirmed",
                "htmlLink": "https://calendar.google.com/p1",
            }
        ],
        "classroom-1": [
            {
                "id": "c1",
                "summary": "Classroom assignment deadline",
                "start": {"date": (today + timedelta(days=1)).isoformat()},
                "end": {"date": (today + timedelta(days=2)).isoformat()},
                "status": "confirmed",
                "htmlLink": "https://calendar.google.com/c1",
            },
            {
                "id": "c2",
                "summary": "Cancelled classroom event",
                "start": {"dateTime": f"{today.isoformat()}T14:00:00+07:00"},
                "end": {"dateTime": f"{today.isoformat()}T15:00:00+07:00"},
                "status": "cancelled",
            },
        ],
        "holiday-vn": [
            {
                "id": "h1",
                "summary": "Public holiday",
                "start": {"date": today.isoformat()},
                "end": {"date": (today + timedelta(days=1)).isoformat()},
                "status": "confirmed",
            }
        ],
    }
    return calendars, events


def install_fake_calendar(monkeypatch, service: FakeCalendarService) -> None:
    monkeypatch.setattr("backend.app.services.integrations.google_token_store.GoogleTokenStore.is_connected", lambda self, user_id, integration: True)
    monkeypatch.setattr("backend.app.services.integrations.google_token_store.GoogleTokenStore.refresh_if_needed", lambda self, user_id, integration: {"access_token": "token"})
    monkeypatch.setattr("backend.app.services.connectors.calendar_real_connector.build_calendar_service", lambda user_id, token_store=None: service)


def test_calendar_list_endpoint_returns_primary_classroom_holiday(monkeypatch) -> None:
    calendars, events = calendar_fixture()
    install_fake_calendar(monkeypatch, FakeCalendarService(calendars, events))
    client = TestClient(app)

    response = client.get("/api/google/calendar/calendars", headers=user_headers(client))

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert len(body["calendars"]) == 3
    assert any(item["primary"] for item in body["calendars"])
    assert any(item["is_classroom"] for item in body["calendars"])
    assert any(item["is_holiday"] for item in body["calendars"])


def test_sync_include_all_calendars_fetches_multiple_non_holiday_calendars(monkeypatch) -> None:
    calendars, events = calendar_fixture()
    service = FakeCalendarService(calendars, events)
    install_fake_calendar(monkeypatch, service)
    client = TestClient(app)

    response = client.post(
        "/api/google/calendar/sync",
        headers=user_headers(client),
        json={"use_mock": False, "include_all_calendars": True, "include_holidays": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_mode"] == "real"
    assert {call["calendarId"] for call in service.event_calls} == {"primary", "classroom-1"}
    assert body["calendar_count"] == 2
    assert body["events_count"] == 2


def test_sync_include_holidays_true_includes_holiday_calendar(monkeypatch) -> None:
    calendars, events = calendar_fixture()
    service = FakeCalendarService(calendars, events)
    install_fake_calendar(monkeypatch, service)
    client = TestClient(app)

    response = client.post(
        "/api/google/calendar/sync",
        headers=user_headers(client),
        json={"use_mock": False, "include_all_calendars": True, "include_holidays": True},
    )

    assert response.status_code == 200
    assert {call["calendarId"] for call in service.event_calls} == {"primary", "classroom-1", "holiday-vn"}
    assert response.json()["events_count"] == 3


def test_cancelled_events_excluded_by_default(monkeypatch) -> None:
    calendars, events = calendar_fixture()
    install_fake_calendar(monkeypatch, FakeCalendarService(calendars, events))
    client = TestClient(app)

    response = client.post(
        "/api/google/calendar/sync",
        headers=user_headers(client),
        json={"use_mock": False, "calendar_ids": ["classroom-1"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["events_count"] == 1
    assert all(event["status"] != "cancelled" for event in body["events"])


def test_processed_events_include_calendar_metadata_and_all_day(monkeypatch) -> None:
    calendars, events = calendar_fixture()
    install_fake_calendar(monkeypatch, FakeCalendarService(calendars, events))
    client = TestClient(app)

    response = client.post(
        "/api/google/calendar/sync",
        headers=user_headers(client),
        json={"use_mock": False, "calendar_ids": ["classroom-1"]},
    )

    assert response.status_code == 200
    event = response.json()["events"][0]
    assert event["calendar_id"] == "classroom-1"
    assert event["calendar_name"] == "Classroom Data Mining"
    assert event["is_all_day"] is True
    assert event["source_mode"] == "real"

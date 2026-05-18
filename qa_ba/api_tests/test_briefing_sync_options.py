from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.api.google import calendar_days_for_range, gmail_query_for_range
from backend.app.main import app
from qa_ba.api_tests.auth_helpers import user_headers


def test_gmail_range_maps_to_query() -> None:
    assert gmail_query_for_range("7d") == "newer_than:7d"
    assert gmail_query_for_range("30d") == "newer_than:30d"
    assert gmail_query_for_range("90d") == "newer_than:90d"
    assert gmail_query_for_range("1y") == "newer_than:365d"
    assert gmail_query_for_range("all_recent") == ""


def test_calendar_range_maps_to_days() -> None:
    assert calendar_days_for_range("7d") == 7
    assert calendar_days_for_range("30d") == 30
    assert calendar_days_for_range("90d") == 90
    assert calendar_days_for_range("1y") == 365


def test_gmail_max_results_cap_enforced() -> None:
    client = TestClient(app)
    headers = user_headers(client)
    response = client.post("/api/google/gmail/sync", headers=headers, json={"max_results": 3000, "use_mock": True})
    assert response.status_code == 422


def test_mock_mode_only_when_explicit() -> None:
    client = TestClient(app)
    headers = user_headers(client)

    not_connected = client.post("/api/google/gmail/sync", headers=headers, json={"use_mock": False, "range": "7d"})
    mock = client.post("/api/google/gmail/sync", headers=headers, json={"use_mock": True, "scenario": "student_clean"})

    assert not_connected.status_code == 200
    assert not_connected.json()["source_mode"] != "mock"
    assert mock.status_code == 200
    assert mock.json()["source_mode"] == "mock"


def test_sync_status_endpoint_returns_status() -> None:
    client = TestClient(app)
    headers = user_headers(client)
    response = client.get("/api/google/sync-status?type=gmail", headers=headers)
    assert response.status_code == 200
    assert response.json()["integration"] == "gmail"

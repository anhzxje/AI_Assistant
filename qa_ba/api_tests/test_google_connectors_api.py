"""FastAPI tests for read-only Google personal connectors using mock data."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from backend.app.main import app


def test_google_status_is_read_only() -> None:
    client = TestClient(app)
    response = client.get("/api/google/status")

    assert response.status_code == 200
    body = response.json()
    assert body["read_only"] is True
    assert body["mode"] in {"mock_fallback", "oauth_readonly"}
    assert "https://www.googleapis.com/auth/gmail.readonly" in body["scopes"]


def test_gmail_sync_and_summary_mock() -> None:
    client = TestClient(app)
    user_id = f"test-{uuid.uuid4()}"

    sync = client.post(
        "/api/google/gmail/sync",
        json={"user_id": user_id, "max_results": 2, "use_mock": True},
    )
    assert sync.status_code == 200
    body = sync.json()
    assert body["mode"] == "mock"
    assert body["records_synced"] == 2
    assert "data" in body["raw_path"]
    assert body["features_path"].endswith("tasks_from_email.jsonl")

    summary = client.get(f"/api/google/gmail/summary?user_id={user_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["total_messages"] == 2
    assert summary_body["unread_count"] >= 1


def test_calendar_sync_and_today_mock() -> None:
    client = TestClient(app)
    user_id = f"test-{uuid.uuid4()}"

    sync = client.post(
        "/api/google/calendar/sync",
        json={"user_id": user_id, "days_ahead": 7, "use_mock": True},
    )
    assert sync.status_code == 200
    assert sync.json()["mode"] == "mock"
    assert sync.json()["records_synced"] >= 1

    today = client.get(f"/api/google/calendar/today?user_id={user_id}")
    assert today.status_code == 200
    assert len(today.json()["events"]) >= 1


def test_daily_briefing_combines_personal_sources() -> None:
    client = TestClient(app)
    user_id = f"test-{uuid.uuid4()}"
    client.post("/api/google/gmail/sync", json={"user_id": user_id, "max_results": 3, "use_mock": True})
    client.post("/api/google/calendar/sync", json={"user_id": user_id, "days_ahead": 7, "use_mock": True})
    client.post("/api/tasks", json={"user_id": user_id, "title": "Review demo priorities", "priority": "high"})

    response = client.get(f"/api/assistant/daily-briefing?user_id={user_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["email_summary"]["total_messages"] >= 1
    assert len(body["today_events"]) >= 1
    assert len(body["priorities"]) >= 1
    assert any(task["title"] == "Review demo priorities" for task in body["task_memory"])

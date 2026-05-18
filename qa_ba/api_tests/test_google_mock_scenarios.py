"""Tests for rich Google/Gmail/Calendar mock scenarios."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from backend.app.main import app


def test_student_clean_sync_returns_clean_emails_and_events() -> None:
    client = TestClient(app)
    user_id = f"scenario-clean-{uuid.uuid4()}"

    gmail = client.post(
        "/api/google/gmail/sync",
        json={"user_id": user_id, "max_results": 20, "use_mock": True, "scenario": "student_clean"},
    )
    calendar = client.post(
        "/api/google/calendar/sync",
        json={"user_id": user_id, "days_ahead": 14, "use_mock": True, "scenario": "student_clean"},
    )

    assert gmail.status_code == 200
    assert gmail.json()["records_synced"] >= 8
    assert gmail.json()["mode"] == "mock:student_clean"
    assert calendar.status_code == 200
    assert calendar.json()["records_synced"] >= 2

    summary = client.get(f"/api/google/gmail/summary?user_id={user_id}").json()
    today = client.get(f"/api/google/calendar/today?user_id={user_id}").json()
    assert summary["important_count"] >= 2
    assert summary["noise_count"] == 0
    assert len(today["events"]) >= 2


def test_student_noisy_sync_filters_noise_in_daily_briefing() -> None:
    client = TestClient(app)
    user_id = f"scenario-noisy-{uuid.uuid4()}"

    client.post("/api/google/gmail/sync", json={"user_id": user_id, "max_results": 30, "use_mock": True, "scenario": "student_noisy"})
    client.post("/api/google/calendar/sync", json={"user_id": user_id, "days_ahead": 14, "use_mock": True, "scenario": "student_noisy"})
    briefing = client.get(f"/api/assistant/daily-briefing?user_id={user_id}")

    assert briefing.status_code == 200
    body = briefing.json()
    assert body["email_summary"]["total_messages"] >= 20
    assert body["ignored_noise_count"] >= 10
    assert "bỏ qua" in body["summary"]
    assert all(item["category"] not in {"spam", "promotion", "social"} for item in body["important_emails"])


def test_empty_new_user_returns_empty_state() -> None:
    client = TestClient(app)
    user_id = f"scenario-empty-{uuid.uuid4()}"

    client.post("/api/google/gmail/sync", json={"user_id": user_id, "use_mock": True, "scenario": "empty_new_user"})
    client.post("/api/google/calendar/sync", json={"user_id": user_id, "use_mock": True, "scenario": "empty_new_user"})
    body = client.get(f"/api/assistant/daily-briefing?user_id={user_id}").json()

    assert body["email_summary"]["total_messages"] == 0
    assert body["today_events"] == []
    assert body["tasks"] == []
    assert "chưa có email hoặc lịch" in body["summary"]


def test_deadline_heavy_extracts_high_priority_tasks() -> None:
    client = TestClient(app)
    user_id = f"scenario-deadline-{uuid.uuid4()}"

    client.post(
        "/api/google/gmail/sync",
        json={"user_id": user_id, "max_results": 30, "use_mock": True, "scenario": "student_deadline_heavy"},
    )
    body = client.get(f"/api/assistant/daily-briefing?user_id={user_id}").json()

    high_tasks = [task for task in body["tasks"] if task.get("priority") == "high"]
    assert len(high_tasks) >= 5
    assert any("Deadline" in task["title"] or "deadline" in task["title"].lower() for task in high_tasks)


def test_scenario_fallback_from_seed_user_id() -> None:
    client = TestClient(app)
    login = client.post(
        "/api/auth/login",
        json={"email": "student.noisy@omni.local", "password": "test123456"},
    )
    assert login.status_code == 200
    user_id = login.json()["user"]["user_id"]

    response = client.post("/api/google/gmail/sync", json={"user_id": user_id, "max_results": 30, "use_mock": True})

    assert response.status_code == 200
    assert response.json()["mode"] == "mock:student_noisy"
    assert response.json()["records_synced"] >= 20


def test_existing_default_mock_still_works_for_unknown_scenario() -> None:
    client = TestClient(app)
    user_id = f"default-mock-{uuid.uuid4()}"

    response = client.post(
        "/api/google/gmail/sync",
        json={"user_id": user_id, "max_results": 2, "use_mock": True, "scenario": "does_not_exist"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "mock"
    assert response.json()["records_synced"] == 2

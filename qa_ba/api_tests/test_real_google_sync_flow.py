"""Real-mode Google sync tests with mocked Google adapters."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from qa_ba.api_tests.auth_helpers import user_headers


def test_use_mock_false_connected_calls_real_gmail_connector(monkeypatch) -> None:
    client = TestClient(app)
    headers = user_headers(client)

    monkeypatch.setattr("backend.app.services.integrations.google_token_store.GoogleTokenStore.is_connected", lambda self, user_id, integration: True)

    def fake_sync_gmail_readonly(**kwargs):
        return [
            {
                "id": "real-1",
                "thread_id": "thread-1",
                "from": "teacher@example.com",
                "to": "student@example.com",
                "subject": "Thông báo lịch thi môn Khai phá dữ liệu",
                "snippet": "Hạn nộp báo cáo trước 17h thứ Sáu",
                "body": "Hạn nộp báo cáo trước 17h thứ Sáu",
                "date": "2026-05-16T09:00:00+07:00",
                "labels": ["INBOX", "UNREAD", "IMPORTANT"],
                "is_unread": True,
                "is_important": True,
                "category": "deadline",
                "priority_hint": "high",
                "expected_task": True,
            }
        ]

    monkeypatch.setattr("backend.app.services.connectors.gmail_connector.sync_gmail_readonly", fake_sync_gmail_readonly)

    response = client.post(
        "/api/google/gmail/sync",
        headers=headers,
        json={"use_mock": False, "max_results": 10, "query": "newer_than:90d"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_mode"] == "real"
    assert body["records_synced"] == 1
    assert body["metadata"]["unread_count"] == 1
    assert body["metadata"]["read_count"] == 0


def test_use_mock_true_still_calls_mock_path() -> None:
    client = TestClient(app)

    response = client.post("/api/google/gmail/sync", json={"user_id": "real-flow-mock", "use_mock": True, "scenario": "student_clean"})

    assert response.status_code == 200
    body = response.json()
    assert body["source_mode"] == "mock"
    assert body["mode"] == "mock:student_clean"


def test_daily_briefing_prefers_real_synced_data(monkeypatch) -> None:
    client = TestClient(app)
    headers = user_headers(client)
    monkeypatch.setattr("backend.app.services.integrations.google_token_store.GoogleTokenStore.is_connected", lambda self, user_id, integration: True)
    monkeypatch.setattr(
        "backend.app.services.connectors.gmail_connector.sync_gmail_readonly",
        lambda **kwargs: [
            {
                "id": "real-briefing-1",
                "thread_id": "thread-1",
                "from": "teacher@example.com",
                "to": "student@example.com",
                "subject": "Thông báo lịch thi môn Khai phá dữ liệu",
                "snippet": "Hạn nộp báo cáo trước 17h thứ Sáu",
                "body": "Hạn nộp báo cáo trước 17h thứ Sáu",
                "date": "2026-05-16T09:00:00+07:00",
                "labels": ["INBOX", "UNREAD", "IMPORTANT"],
                "is_unread": True,
                "is_important": True,
                "category": "deadline",
                "priority_hint": "high",
                "expected_task": True,
            }
        ],
    )

    sync = client.post("/api/google/gmail/sync", headers=headers, json={"use_mock": False})
    briefing = client.get("/api/assistant/daily-briefing", headers=headers)

    assert sync.status_code == 200
    assert briefing.status_code == 200
    assert briefing.json()["metadata"]["source_mode"] in {"real", "mixed"}

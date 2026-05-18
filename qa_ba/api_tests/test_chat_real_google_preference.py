"""Chat routes prefer real Google data unless mock mode is explicit."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def fake_gmail_real(**kwargs):
    return [
        {
            "id": "real-chat-email",
            "thread_id": "thread-real",
            "from": "teacher@example.com",
            "to": "student@example.com",
            "subject": "Real Gmail deadline",
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


def fake_calendar_real(**kwargs):
    return [
        {
            "id": "real-chat-event",
            "summary": "Real Calendar meeting",
            "description": "Lab meeting",
            "start": {"dateTime": "2026-05-16T09:00:00+07:00"},
            "end": {"dateTime": "2026-05-16T10:00:00+07:00"},
            "location": "Room 101",
            "attendees": [],
            "status": "confirmed",
            "category": "meeting",
            "priority_hint": "medium",
        }
    ]


def patch_connected(monkeypatch, *, gmail=True, calendar=True) -> None:
    def is_connected(self, user_id, integration):
        return gmail if integration == "gmail" else calendar

    monkeypatch.setattr("backend.app.services.integrations.google_token_store.GoogleTokenStore.is_connected", is_connected)
    monkeypatch.setattr("backend.app.services.connectors.gmail_connector.sync_gmail_readonly", fake_gmail_real)
    monkeypatch.setattr("backend.app.services.connectors.calendar_connector.sync_calendar_readonly", fake_calendar_real)


def post_chat(payload: dict):
    return TestClient(app).post("/api/assistant/chat", json={"user_id": "chat-google-user", "session_id": "chat-google-session", **payload})


def test_gmail_connected_omitted_mock_prefers_real(monkeypatch) -> None:
    patch_connected(monkeypatch)

    response = post_chat({"message": "tóm tắt email của tôi", "include_memory": True})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "gmail"
    assert body["metadata"]["google"]["source_mode"] == "real"
    assert "gmail_real_sync" in body["actions"]
    assert "student_clean" not in str(body)


def test_gmail_connected_false_mock_prefers_real(monkeypatch) -> None:
    patch_connected(monkeypatch)

    response = post_chat({"message": "tôi có email chưa đọc nào không", "use_mock_google": False})

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["google"]["source_mode"] == "real"
    assert body["metadata"]["google"]["unread_count"] == 1


def test_gmail_connected_explicit_mock_uses_mock(monkeypatch) -> None:
    patch_connected(monkeypatch)

    response = post_chat({"message": "tóm tắt email của tôi", "use_mock_google": True})

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["google"]["source_mode"] == "mock"
    assert "gmail_mock_sync" in body["actions"]


def test_gmail_not_connected_without_mock_is_friendly(monkeypatch) -> None:
    patch_connected(monkeypatch, gmail=False, calendar=False)

    response = post_chat({"message": "tóm tắt email của tôi", "use_mock_google": False})

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["google"]["source_mode"] == "not_connected"
    assert "Gmail chưa được kết nối" in body["answer"]


def test_calendar_connected_chat_prefers_real(monkeypatch) -> None:
    patch_connected(monkeypatch)

    response = post_chat({"message": "hôm nay tôi có lịch gì", "use_mock_google": False})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "calendar"
    assert body["metadata"]["google"]["source_mode"] == "real"
    assert "calendar_real_sync" in body["actions"]


def test_daily_briefing_both_connected_source_real(monkeypatch) -> None:
    patch_connected(monkeypatch)

    response = post_chat({"message": "hôm nay tôi cần làm gì", "use_mock_google": False})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "daily_briefing"
    assert body["metadata"]["google"]["source_mode"] == "real"
    assert body["metadata"]["google"]["gmail_source"] == "real"
    assert body["metadata"]["google"]["calendar_source"] == "real"


def test_daily_briefing_only_gmail_connected_source_mixed(monkeypatch) -> None:
    patch_connected(monkeypatch, gmail=True, calendar=False)

    response = post_chat({"message": "hôm nay tôi cần làm gì", "use_mock_google": False})

    assert response.status_code == 200
    google = response.json()["metadata"]["google"]
    assert google["source_mode"] == "mixed"
    assert google["gmail_source"] == "real"
    assert google["calendar_source"] == "none"

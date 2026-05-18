from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from qa_ba.api_tests.auth_helpers import user_headers


def test_action_studio_endpoints_require_auth() -> None:
    client = TestClient(app)
    response = client.post("/api/action-studio/report", json={"period": "today", "style": "student"})
    assert response.status_code == 401


def test_meeting_prep_returns_markdown_sections() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/action-studio/meeting-prep",
        headers=user_headers(client),
        json={"query": "Chuẩn bị cho cuộc họp gần nhất"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["draft_type"] == "meeting_prep"
    assert "Chuẩn bị cuộc họp" in body["content"]
    assert "### 1." in body["content"]
    assert body["metadata"]["warning"] == "Draft only. Review before use."


def test_report_returns_structured_markdown() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/action-studio/report",
        headers=user_headers(client),
        json={"period": "today", "style": "student"},
    )
    assert response.status_code == 200
    content = response.json()["content"]
    assert "# Báo cáo công việc" in content
    assert "## Tóm tắt" in content
    assert "## Kế hoạch tiếp theo" in content


def test_slides_returns_marp_markdown() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/action-studio/slides",
        headers=user_headers(client),
        json={"topic": "Lumi demo", "slide_count": 6, "source": "latest_briefing"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["draft_type"] == "slides"
    assert "marp: true" in body["content"]
    assert "## Agenda" in body["content"]


def test_email_draft_returns_subject_and_body_json_text() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/action-studio/email-draft",
        headers=user_headers(client),
        json={"instruction": "viết phản hồi lịch sự", "tone": "formal", "language": "vi"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["draft_type"] == "email_draft"
    assert '"subject"' in body["content"]
    assert '"body"' in body["content"]
    assert body["metadata"]["no_send"] is True
    assert body["metadata"]["no_gmail_draft"] is True


def test_no_google_write_action_endpoints_exist() -> None:
    client = TestClient(app)
    headers = user_headers(client)
    for path in [
        "/api/action-studio/send-email",
        "/api/action-studio/create-gmail-draft",
        "/api/action-studio/calendar/create",
        "/api/google/calendar/create",
    ]:
        response = client.post(path, headers=headers, json={})
        assert response.status_code in {404, 405}


def test_drafts_are_scoped_to_authenticated_user() -> None:
    client = TestClient(app)
    headers = user_headers(client)
    user2_login = client.post("/api/auth/login", json={"email": "user2@omni.local", "password": "user2123456"})
    assert user2_login.status_code == 200
    user2_headers = {"Authorization": f"Bearer {user2_login.json()['access_token']}"}
    created = client.post(
        "/api/action-studio/report",
        headers=headers,
        json={"period": "7d", "style": "student"},
    )
    assert created.status_code == 200
    draft_id = created.json()["draft_id"]

    fetched = client.get(f"/api/action-studio/{draft_id}", headers=headers)
    recent = client.get("/api/action-studio/recent", headers=headers)

    assert fetched.status_code == 200
    assert fetched.json()["draft_id"] == draft_id
    assert recent.status_code == 200
    assert all(item["user_id"] == created.json()["user_id"] for item in recent.json()["drafts"])

    forbidden = client.get(f"/api/action-studio/{draft_id}", headers=user2_headers)
    user2_recent = client.get("/api/action-studio/recent", headers=user2_headers)
    assert forbidden.status_code == 404
    assert all(item["user_id"] != created.json()["user_id"] for item in user2_recent.json()["drafts"])


def test_chat_action_studio_intent_creates_draft() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/assistant/chat",
        headers=user_headers(client),
        json={"message": "chuẩn bị cho cuộc họp hôm nay", "session_id": "action-studio-test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "action_studio"
    assert "Đây là bản nháp" in body["answer"]
    assert "/action-studio" not in body["answer"]
    assert body["metadata"]["action_studio"]["draft_type"] == "meeting_prep"
    assert "draft_only_no_write" in body["actions"]

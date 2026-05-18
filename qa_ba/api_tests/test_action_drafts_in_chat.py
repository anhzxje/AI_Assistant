from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from orchestration.intent_classifier_v2 import classify_intent_v2
from qa_ba.api_tests.auth_helpers import user_headers


def test_meeting_prep_query_returns_draft_directly_in_chat() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/assistant/chat",
        headers=user_headers(client),
        json={"message": "chuẩn bị cho cuộc họp hôm nay", "session_id": "draft-direct-test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "action_studio"
    assert "Đây là bản nháp" in body["answer"]
    assert "/action-studio" not in body["answer"]
    assert body["metadata"]["action_studio"]["draft_type"] == "meeting_prep"
    assert "draft_only_no_write" in body["actions"]


def test_slide_generation_not_exposed_in_chat_or_nav() -> None:
    assert classify_intent_v2("tạo slide cho buổi họp").intent != "action_studio"

    nav = Path("frontend/components/layout/AppNav.tsx").read_text(encoding="utf-8")
    assert "/action-studio" not in nav
    assert "Action Studio" not in nav

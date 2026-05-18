"""Tests for the upgraded assistant brain."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.conversation.context_builder import ConversationContext
from orchestration.intent_classifier_v2 import classify_intent_v2


def test_classifier_v2_routes_general_chat() -> None:
    result = classify_intent_v2("giải thích AI là gì")

    assert result.intent == "general_chat"


def test_classifier_v2_routes_followup_to_previous_topic() -> None:
    context = ConversationContext(
        recent_messages=[],
        conversation_summary="Last topic: khoa học dữ liệu",
        has_followup_reference=True,
        last_topic_hint="khoa học dữ liệu học những môn gì",
        last_sources=[],
        previous_intent="institutional_rag",
    )

    result = classify_intent_v2("ngành này có học lập trình không?", context)

    assert result.intent == "institutional_rag"
    assert result.rewritten_query


def test_brain_institutional_query(monkeypatch) -> None:
    install_fake_retriever(monkeypatch)
    response = post_chat(
        "khoa học dữ liệu học những môn gì",
        user_id=f"test-{uuid.uuid4()}",
        session_id=f"session-{uuid.uuid4()}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] in {"institutional_rag", "rag"}
    assert body["answer"]
    assert len(body["sources"]) > 0


def test_brain_daily_briefing() -> None:
    response = post_chat(
        "hôm nay tôi cần làm gì",
        user_id=f"test-{uuid.uuid4()}",
        session_id=f"session-{uuid.uuid4()}",
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "daily_briefing"


def test_brain_general_chat_disabled_without_ollama(monkeypatch) -> None:
    from orchestration.nodes import general_chat_node

    class FakeOllama:
        def is_available(self) -> bool:
            return False

    monkeypatch.setattr(general_chat_node, "OllamaService", FakeOllama)
    response = post_chat(
        "bạn là ai",
        user_id=f"test-{uuid.uuid4()}",
        session_id=f"session-{uuid.uuid4()}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "general_chat"
    assert "Ollama" in body["answer"]
    assert body["metadata"]["general_llm_mode"] == "disabled"


def test_brain_followup_uses_last_topic(monkeypatch) -> None:
    install_fake_retriever(monkeypatch)
    user_id = f"test-{uuid.uuid4()}"
    session_id = f"session-{uuid.uuid4()}"

    first = post_chat("khoa học dữ liệu ở HUS học những môn gì", user_id=user_id, session_id=session_id)
    assert first.status_code == 200

    followup = post_chat("ngành này có học lập trình không?", user_id=user_id, session_id=session_id)
    assert followup.status_code == 200
    body = followup.json()
    assert body["metadata"]["conversation_used"] is True
    assert body["intent"] in {"institutional_rag", "rag"}
    assert body["answer"]
    assert body["metadata"]["intent_classifier"]["rewritten_query"]


def test_brain_clarifies_empty_followup_context() -> None:
    response = post_chat(
        "cái đó thì sao?",
        user_id=f"test-{uuid.uuid4()}",
        session_id=f"session-{uuid.uuid4()}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "clarification"
    assert "Bạn muốn hỏi tiếp" in body["answer"]


def install_fake_retriever(monkeypatch) -> None:
    from data_platform.feature_store.embeddings.retriever import RetrievalResult
    from orchestration.nodes import rag_node

    class FakeRetrieverService:
        collection = "test_collection"
        embedding_model_name = "test_embedding"

        def retrieve(self, query: str, *, top_k: int):
            return [
                RetrievalResult(
                    title="Khoa hoc du lieu",
                    document_type="program",
                    score=0.9,
                    vector_score=0.9,
                    source_url="https://example.edu/program",
                    text="Khoa hoc du lieu co hoc phan lap trinh, thong ke, hoc may va khai pha du lieu.",
                    payload={"chunk_id": "chunk-test"},
                )
            ]

    monkeypatch.setattr(rag_node, "get_retriever_service", lambda: FakeRetrieverService())


def post_chat(message: str, *, user_id: str, session_id: str):
    client = TestClient(app)
    return client.post(
        "/api/assistant/chat",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": message,
            "include_memory": True,
            "use_mock_google": True,
        },
    )

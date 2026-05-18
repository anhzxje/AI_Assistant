"""FastAPI tests for assistant orchestration routes."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from backend.app.main import app


def test_assistant_rag_route(monkeypatch) -> None:
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
                    text="Khoa hoc du lieu co cac hoc phan ve lap trinh, thong ke va hoc may.",
                    payload={"chunk_id": "chunk-test"},
                )
            ]

    monkeypatch.setattr(rag_node, "get_retriever_service", lambda: FakeRetrieverService())
    response = post_chat("khoa hoc du lieu hoc nhung mon gi")

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] in {"institutional_rag", "rag"}
    assert body["sources"]
    assert "rag_node" in body["metadata"]["route"]
    assert body["metadata"]["intent_classifier"]["intent"] == "institutional_rag"


def test_assistant_rag_followup_uses_session_context(monkeypatch) -> None:
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
                    text="Khoa hoc du lieu co cac hoc phan ve lap trinh, thong ke va hoc may.",
                    payload={"chunk_id": "chunk-test"},
                )
            ]

    monkeypatch.setattr(rag_node, "get_retriever_service", lambda: FakeRetrieverService())
    client = TestClient(app)
    session_id = f"session-{uuid.uuid4()}"
    user_id = f"test-{uuid.uuid4()}"

    first = client.post(
        "/api/assistant/chat",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "khoa hoc du lieu o HUS",
            "include_memory": True,
            "use_mock_google": True,
        },
    )
    assert first.status_code == 200

    followup = client.post(
        "/api/assistant/chat",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "message": "nganh do hoc nhung mon gi",
            "include_memory": True,
            "use_mock_google": True,
        },
    )

    assert followup.status_code == 200
    body = followup.json()
    assert body["intent"] in {"institutional_rag", "rag"}
    assert body["metadata"]["conversation_used"] is True
    assert body["metadata"]["intent_classifier"]["rewritten_query"]
    assert "khoa hoc du lieu" in body["metadata"]["intent_classifier"]["rewritten_query"]


def test_assistant_memory_route() -> None:
    response = post_chat(
        "hay nho toi dang lam do an OmniAssistant",
        user_id=f"test-{uuid.uuid4()}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] in {"personal_memory", "memory"}
    assert body["memory_used"] is True


def test_assistant_tasks_route() -> None:
    client = TestClient(app)
    user_id = f"test-{uuid.uuid4()}"
    client.post("/api/tasks", json={"user_id": user_id, "title": "Finish orchestration tests"})

    response = post_chat("toi co task nao chua xong", user_id=user_id)

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "tasks"
    assert "Finish orchestration tests" in body["answer"]


def test_assistant_gmail_route_mock() -> None:
    response = post_chat("tom tat email", user_id=f"test-{uuid.uuid4()}")

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "gmail"
    assert body["sources"]
    assert "gmail_readonly_sync" in body["actions"]


def test_assistant_calendar_route_mock() -> None:
    response = post_chat("lich hom nay cua toi", user_id=f"test-{uuid.uuid4()}")

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "calendar"
    assert body["sources"]


def test_assistant_daily_briefing_route() -> None:
    response = post_chat("hom nay toi can lam gi", user_id=f"test-{uuid.uuid4()}")

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "daily_briefing"
    assert "Daily briefing" in body["answer"]


def test_assistant_fallback_route() -> None:
    response = post_chat("abracadabra xyz")

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "fallback"
    assert "Mình" in body["answer"]


def post_chat(message: str, *, user_id: str = "default"):
    client = TestClient(app)
    return client.post(
        "/api/assistant/chat",
        json={
            "user_id": user_id,
            "session_id": "test-session",
            "message": message,
            "include_memory": True,
            "use_mock_google": True,
        },
    )

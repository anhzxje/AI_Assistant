"""FastAPI tests for personal memory and task APIs."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from backend.app.main import app


def test_remember_fact_and_query_memory() -> None:
    client = TestClient(app)
    user_id = f"test-{uuid.uuid4()}"

    remember = client.post(
        "/api/memory/remember",
        json={
            "user_id": user_id,
            "session_id": "s-test",
            "text": "Remember that I prefer concise answers.",
            "memory_type": "preference",
        },
    )
    assert remember.status_code == 200
    body = remember.json()
    assert len(body["saved_memories"]) == 1
    assert body["saved_memories"][0]["memory_type"] == "preference"

    query = client.post(
        "/api/memory/query",
        json={"user_id": user_id, "session_id": "s-test", "query": "concise answers"},
    )
    assert query.status_code == 200
    assert len(query.json()["long_term_memories"]) >= 1


def test_create_update_delete_task() -> None:
    client = TestClient(app)
    user_id = f"test-{uuid.uuid4()}"

    created = client.post(
        "/api/tasks",
        json={
            "user_id": user_id,
            "title": "Submit Data Mining report",
            "priority": "high",
        },
    )
    assert created.status_code == 200
    task = created.json()
    assert task["status"] == "open"

    updated = client.patch(
        f"/api/tasks/{task['task_id']}?user_id={user_id}",
        json={"status": "done", "priority": "medium"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"
    assert updated.json()["priority"] == "medium"

    deleted = client.delete(f"/api/tasks/{task['task_id']}?user_id={user_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_delete_memory() -> None:
    client = TestClient(app)
    user_id = f"test-{uuid.uuid4()}"
    created = client.post(
        "/api/memory/remember",
        json={"user_id": user_id, "text": "Remember that my thesis topic is RAG evaluation."},
    )
    assert created.status_code == 200
    memory_id = created.json()["saved_memories"][0]["memory_id"]

    deleted = client.delete(f"/api/memory/{memory_id}?user_id={user_id}")
    assert deleted.status_code == 200
    assert deleted.json()["id"] == memory_id


def test_memory_summary() -> None:
    client = TestClient(app)
    user_id = f"test-{uuid.uuid4()}"
    client.post("/api/memory/remember", json={"user_id": user_id, "text": "Remember this test fact."})
    client.post("/api/tasks", json={"user_id": user_id, "title": "Memory summary task"})

    response = client.get(f"/api/memory/summary?user_id={user_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["long_term_memories_count"] >= 1
    assert body["tasks_count"] >= 1
    assert "long_term" in body["storage_mode"]


def test_rag_query_accepts_memory_fields(monkeypatch) -> None:
    from backend.app.api import rag as rag_api
    from data_platform.feature_store.embeddings.retriever import RetrievalResult

    class FakeRetrieverService:
        collection = "test_collection"
        embedding_model_name = "test_embedding"

        def retrieve(self, query: str, *, top_k: int):
            return [
                RetrievalResult(
                    title="Test document",
                    document_type="program",
                    score=0.9,
                    vector_score=0.9,
                    source_url="https://example.edu",
                    text="Khoa hoc du lieu co cac hoc phan ve lap trinh va thong ke.",
                    payload={"chunk_id": "chunk-test"},
                )
            ]

    monkeypatch.setattr(rag_api, "get_retriever_service", lambda: FakeRetrieverService())
    client = TestClient(app)
    response = client.post(
        "/api/rag/query",
        json={
            "query": "khoa hoc du lieu hoc gi",
            "top_k": 3,
            "use_llm": False,
            "user_id": f"test-{uuid.uuid4()}",
            "session_id": "s-rag-memory",
            "include_memory": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["mode"] == "extractive_fallback"
    assert "memory_items" in body["metadata"]

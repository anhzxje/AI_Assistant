"""FastAPI tests for the RAG API.

Run with:
    python -m pytest qa_ba/api_tests
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["qdrant"] in {"available", "embedded", "unavailable"}
    assert body["llm"] in {"ollama", "fallback", "unavailable"}


def test_rag_query_valid(monkeypatch) -> None:
    from backend.app.api import rag as rag_api
    from data_platform.feature_store.embeddings.retriever import RetrievalResult

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
                    source_url="https://example.edu",
                    text="Khoa hoc du lieu co cac hoc phan ve lap trinh, thong ke va khai pha du lieu.",
                    payload={"chunk_id": "test-chunk"},
                )
            ]

    monkeypatch.setattr(rag_api, "get_retriever_service", lambda: FakeRetrieverService())
    client = TestClient(app)
    response = client.post(
        "/api/rag/query",
        json={"query": "khoa hoc du lieu hoc nhung mon gi", "top_k": 3, "use_llm": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert len(body["citations"]) <= 3
    assert body["metadata"]["mode"] in {"ollama", "extractive_fallback"}


def test_rag_query_rejects_empty_query() -> None:
    client = TestClient(app)
    response = client.post("/api/rag/query", json={"query": "", "top_k": 3})

    assert response.status_code == 422


def test_rag_query_rejects_top_k_out_of_range() -> None:
    client = TestClient(app)
    response = client.post("/api/rag/query", json={"query": "test", "top_k": 100})

    assert response.status_code == 422

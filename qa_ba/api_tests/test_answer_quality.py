"""Tests for assistant answer quality diagnostics."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.quality.answer_diagnostics import diagnose_answer


def test_assistant_chat_metadata_includes_quality(monkeypatch) -> None:
    install_fake_retriever(monkeypatch)
    client = TestClient(app)
    response = client.post(
        "/api/assistant/chat",
        json={
            "user_id": f"test-{uuid.uuid4()}",
            "session_id": f"session-{uuid.uuid4()}",
            "message": "khoa học dữ liệu học những môn gì",
            "include_memory": True,
            "use_mock_google": True,
        },
    )

    assert response.status_code == 200
    quality = response.json()["metadata"]["quality"]
    assert "quality_score" in quality
    assert "issues" in quality
    assert "requires_admin_review" in quality


def test_diagnostics_catches_rag_answer_without_sources() -> None:
    result = diagnose_answer(
        query="khoa học dữ liệu học những môn gì",
        answer="Khoa học dữ liệu có học lập trình.",
        intent="institutional_rag",
        sources=[],
        metadata={},
        latency_ms=100,
    )

    assert "rag_intent_without_sources" in result["issues"]
    assert result["suggested_feedback_reason"] == "missing_source"
    assert result["requires_admin_review"] is True


def test_diagnostics_allows_source_cards_without_inline_markers() -> None:
    result = diagnose_answer(
        query="khoa học dữ liệu học những môn gì",
        answer="Khoa học dữ liệu có học lập trình.",
        intent="institutional_rag",
        sources=[{"source_url": "https://example.edu", "score": 0.8}],
        metadata={},
        latency_ms=100,
    )

    assert "sources_without_citation_markers" not in result["issues"]
    assert result["suggested_feedback_reason"] == "other"


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

"""Regression tests for source usage and authenticated user routing."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.citation_service import build_citations
from data_platform.feature_store.embeddings.retriever import RetrievalResult


def make_result(index: int, *, document_type: str = "leadership") -> RetrievalResult:
    return RetrievalResult(
        title=f"Source {index}",
        document_type=document_type,
        score=0.9 - (index * 0.01),
        vector_score=0.9 - (index * 0.01),
        source_url=f"https://hus.vnu.edu.vn/source-{index}",
        text="Official source text about HUS leadership and rector." * 4,
        payload={"chunk_id": f"chunk-{index}"},
    )


def test_cited_sources_are_separated_from_debug_retrieval() -> None:
    results = [
        make_result(1),
        make_result(2, document_type="admission"),
        make_result(3, document_type="announcement"),
    ]

    visible = build_citations(results, answer="The answer uses the first source [1].", query="hieu truong HUS la ai")
    debug = build_citations(
        results,
        answer="The answer uses the first source [1].",
        query="hieu truong HUS la ai",
        cited_only=False,
    )

    assert len(visible) == 1
    assert visible[0].citation_index == 1
    assert visible[0].usage == "cited"
    assert visible[0].used_in_answer is True
    assert len(debug) == 3
    assert debug[1].usage == "retrieval_debug"
    assert debug[1].used_in_answer is False


def test_authenticated_chat_uses_token_user_id(monkeypatch) -> None:
    from backend.app.api import assistant as assistant_api

    captured: dict[str, str] = {}

    class FakeGraph:
        def invoke(self, **kwargs):
            captured["user_id"] = kwargs["user_id"]
            return {
                "answer": "ok",
                "intent": "general_chat",
                "sources": [],
                "actions": [],
                "memory_used": False,
                "metadata": {"latency_ms": 0, "route": ["fake"]},
            }

    monkeypatch.setattr(assistant_api, "get_assistant_graph", lambda: FakeGraph())
    client = TestClient(app)
    login_response = client.post(
        "/api/auth/login",
        json={"email": "user@omni.local", "password": "user123456"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/assistant/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_id": "admin",
            "session_id": "test-session",
            "message": "xin chao",
            "include_memory": True,
            "use_mock_google": True,
        },
    )

    assert response.status_code == 200
    assert captured["user_id"] != "admin"
    assert captured["user_id"]

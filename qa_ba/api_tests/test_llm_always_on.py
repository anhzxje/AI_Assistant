from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.answer_service import AnswerService
from backend.app.services.llm_service import OllamaService
from data_platform.feature_store.embeddings.retriever import RetrievalResult
from orchestration.nodes import general_chat_node


def test_health_reports_ollama_when_available() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    expected = "ollama" if OllamaService().is_available() else "fallback"
    assert response.json()["llm"] == expected


def test_general_chat_uses_llm_when_available(monkeypatch) -> None:
    class FakeOllama:
        last_latency_ms = 12
        last_error = None

        def is_available(self) -> bool:
            return True

        def generate(self, prompt: str, *, temperature: float = 0.1, num_ctx: int = 4096) -> str:
            return "AI là trí tuệ nhân tạo."

    monkeypatch.setattr(general_chat_node, "OllamaService", FakeOllama)
    state = {
        "message": "giải thích AI là gì",
        "user_id": "test-user",
        "session_id": "test-session",
        "include_memory": False,
        "metadata": {},
        "conversation_context": {},
        "auth_role": "user",
    }

    result = general_chat_node.run(state)

    assert result["metadata"]["general_llm_mode"] == "ollama"
    assert "AI" in result["answer"]


def test_general_chat_retries_with_chat_before_disabling(monkeypatch) -> None:
    class FakeOllama:
        last_latency_ms = 12
        last_error = None

        def __init__(self) -> None:
            self.generate_calls = 0

        def is_available(self) -> bool:
            return True

        def warmup(self) -> bool:
            return True

        def generate(self, prompt: str, *, temperature: float = 0.1, num_ctx: int = 4096) -> str | None:
            self.generate_calls += 1
            return None

        def chat(self, messages, *, temperature: float = 0.1, num_ctx: int = 4096) -> str | None:
            return "Mình đang dùng local LLM bình thường."

    monkeypatch.setattr(general_chat_node, "OllamaService", FakeOllama)
    state = {
        "message": "giải thích AI là gì",
        "user_id": "test-user",
        "session_id": "test-session",
        "include_memory": False,
        "metadata": {},
        "conversation_context": {},
        "auth_role": "user",
    }

    result = general_chat_node.run(state)

    assert result["metadata"]["general_llm_mode"] == "ollama"
    assert "local LLM" in result["answer"]


def test_rag_metadata_shows_llm_synthesis_when_available() -> None:
    class FakeRetriever:
        collection = "test"
        embedding_model_name = "fake"

        def retrieve(self, query: str, *, top_k: int):
            self.last_timings = {"cache_hit": False, "embedding_latency_ms": 1, "qdrant_latency_ms": 1, "reranking_latency_ms": 1}
            return [
                RetrievalResult(
                    title="Khoa học dữ liệu",
                    document_type="admission",
                    score=0.9,
                    vector_score=0.9,
                    source_url="https://example.edu/khdl",
                    text="Chương trình Khoa học dữ liệu có khoa học máy tính, thống kê và toán ứng dụng.",
                    payload={"chunk_id": "c1", "preview_text": "Chương trình Khoa học dữ liệu có khoa học máy tính, thống kê và toán ứng dụng."},
                )
            ]

    class FakeLlm:
        model = "fake-llm"
        last_latency_ms = 20
        last_error = None

        def is_available(self) -> bool:
            return True

        def generate(self, prompt: str, *, temperature: float = 0.0, num_ctx: int = 2048) -> str:
            return "Ngành này học khoa học máy tính, thống kê và toán ứng dụng [1]."

    response = AnswerService(FakeRetriever(), FakeLlm(), None).answer(
        query="khoa học dữ liệu học những môn gì",
        top_k=5,
        use_llm=True,
        include_memory=False,
    )

    assert response.metadata.mode == "ollama"
    assert response.metadata.llm_generation_latency_ms == 20

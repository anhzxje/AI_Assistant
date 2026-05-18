from __future__ import annotations

import uuid

from backend.app.services.answer_service import AnswerService
from backend.app.services.cache import TTLCache
from data_platform.feature_store.embeddings.retriever import RetrievalResult


class FakeRetriever:
    collection = "test_collection"
    embedding_model_name = "test_embedding"

    def __init__(self, results):
        self.results = results
        self.last_timings = {"cache_hit": False, "embedding_latency_ms": 1, "qdrant_latency_ms": 1, "reranking_latency_ms": 1}

    def retrieve(self, query: str, *, top_k: int):
        return self.results


class FakeLlm:
    model = "fake-llm"
    last_latency_ms = 3
    last_error = None

    def __init__(self, available: bool = True):
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def generate(self, prompt: str, *, temperature: float = 0.0, num_ctx: int = 2048) -> str:
        return "Câu trả lời RAG thông thường từ LLM [1]."


def result(
    *,
    text: str,
    source_url: str = "https://hus.vnu.edu.vn/gioi-thieu/co-cau-to-chuc/ban-giam-hieu",
    document_type: str = "leadership",
    chunk_id: str | None = "chunk-official",
    content_hash: str = "hash-official",
) -> RetrievalResult:
    payload = {"content_hash": content_hash}
    if chunk_id:
        payload["chunk_id"] = chunk_id
    return RetrievalResult(
        title="Ban Giám Hiệu Trường",
        document_type=document_type,
        score=0.95,
        vector_score=0.9,
        source_url=source_url,
        text=text,
        payload=payload,
    )


def answer_for(query: str, results, llm_available: bool = True):
    return AnswerService(FakeRetriever(results), FakeLlm(llm_available), None).answer(
        query=f"{query} {uuid.uuid4()}",
        top_k=5,
        use_llm=True,
        include_memory=False,
    )


def test_leadership_fast_path_works_with_official_source() -> None:
    response = answer_for(
        "hiệu trưởng HUS là ai",
        [
            result(
                text=(
                    "Ban Giám hiệu Trường Đại học Khoa học Tự nhiên. "
                    "GS.TS. Lê Thanh Sơn - Hiệu trưởng."
                )
            )
        ],
    )

    assert response.metadata.mode == "deterministic_fact"
    assert "Lê Thanh Sơn" in response.answer
    assert response.metadata.fast_path["validated"] is True
    assert response.metadata.fast_path["source_hashes"] == ["hash-official"]
    assert response.metadata.fast_path["validated_sources"][0]["chunk_id"] == "chunk-official"


def test_leadership_fast_path_refuses_if_source_missing() -> None:
    response = answer_for(
        "hiệu trưởng HUS là ai",
        [
            result(
                text="GS.TS. Lê Thanh Sơn - Hiệu trưởng.",
                source_url="https://example.edu/not-official",
                document_type="announcement",
            )
        ],
    )

    assert response.metadata.mode == "fast_path_refused"
    assert "Cần kiểm tra nguồn chính thức" in response.answer
    assert response.metadata.fast_path["validated"] is False
    assert "document_type_mismatch" in response.metadata.fast_path["reason"]


def test_leadership_fast_path_refuses_without_required_evidence() -> None:
    response = answer_for(
        "hiệu trưởng HUS là ai",
        [result(text="Ban Giám hiệu Trường Đại học Khoa học Tự nhiên.")],
    )

    assert response.metadata.mode == "fast_path_refused"
    assert response.metadata.fast_path["reason"] == "official_leadership_source_missing"


def test_non_office_fast_path_falls_back_to_normal_rag_when_validation_fails() -> None:
    response = answer_for(
        "ngành này có học lập trình không?",
        [
            result(
                text="Khoa học dữ liệu có học lập trình.",
                source_url="https://example.edu/khdl",
                document_type="admission",
            )
        ],
    )

    assert response.metadata.mode == "ollama"
    assert response.answer == "Câu trả lời RAG thông thường từ LLM [1]."
    assert response.metadata.fast_path["validated"] is False
    assert "source_url_missing" in response.metadata.fast_path["reason"]


def test_fast_path_refuses_when_chunk_id_missing() -> None:
    response = answer_for(
        "hiệu trưởng HUS là ai",
        [result(text="Ban Giám hiệu. GS.TS. Lê Thanh Sơn - Hiệu trưởng.", chunk_id=None)],
    )

    assert response.metadata.mode == "fast_path_refused"
    assert response.metadata.fast_path["reason"] == "chunk_id_missing"


def test_answer_cache_can_be_cleared_after_reindex() -> None:
    cache = TTLCache(namespace="answer", max_items=4)
    key = f"test-{uuid.uuid4()}"
    cache.set(key, {"answer": "cached"}, ttl_seconds=60)

    assert cache.get(key) == {"answer": "cached"}
    cache.delete_prefix()

    assert cache.get(key) is None


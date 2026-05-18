from __future__ import annotations

from backend.app.services.answer_service import AnswerService
from backend.app.services.citation_service import build_citations
from backend.app.services.llm_service import OllamaService
from data_platform.feature_store.embeddings.retriever import RetrievalResult


def test_rag_fallback_synthesizes_instead_of_dumping_chunks() -> None:
    response = AnswerService(
        retriever_service=FakeRetrieverService(),
        llm_service=OllamaService(),
    ).answer(
        query="khoa hoc du lieu hoc nhung mon gi",
        top_k=3,
        use_llm=False,
        include_memory=False,
    )

    assert "Mình tìm thấy các thông tin liên quan" not in response.answer
    assert "[1]" not in response.answer
    assert "- " in response.answer
    assert response.citations
    assert response.citations[0].snippet
    assert len(response.citations[0].snippet or "") <= 181


def test_debug_retrieval_is_separate_from_visible_sources() -> None:
    results = FakeRetrieverService().retrieve("khoa hoc du lieu", top_k=3)
    visible = build_citations(results, answer="Câu trả lời tổng hợp.", query="khoa hoc du lieu", cited_only=True)
    debug = build_citations(results, answer="Câu trả lời tổng hợp.", query="khoa hoc du lieu", cited_only=False)

    assert all(item.usage != "retrieval_debug" for item in visible)
    assert any(item.usage == "retrieval_debug" for item in debug[1:])


class FakeRetrieverService:
    collection = "test_collection"
    embedding_model_name = "test_embedding"
    last_timings: dict = {}

    def retrieve(self, query: str, *, top_k: int):
        long_text = (
            "Khoa hoc du lieu co cac hoc phan ve lap trinh, co so du lieu, thong ke, "
            "toan ung dung, hoc may, khai pha du lieu va thuc hanh phan tich du lieu. "
            "Sinh vien duoc ren luyen ky nang mo hinh hoa va ung dung du lieu trong nhieu linh vuc."
        )
        return [
            RetrievalResult(
                title="Khoa hoc du lieu",
                document_type="program",
                score=0.9,
                vector_score=0.9,
                source_url="https://example.edu/program",
                text=long_text,
                payload={"chunk_id": "chunk-quality", "preview_text": long_text},
            ),
            RetrievalResult(
                title="Chuong trinh dao tao",
                document_type="program",
                score=0.82,
                vector_score=0.82,
                source_url="https://example.edu/curriculum",
                text="Chuong trinh nhan manh lap trinh, thong ke va hoc may.",
                payload={"chunk_id": "chunk-quality-2"},
            ),
        ]

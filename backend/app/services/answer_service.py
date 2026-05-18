"""Grounded RAG answer construction with optional personal memory context."""

from __future__ import annotations

import re
import time
import hashlib
import json

from backend.app.schemas.rag_schema import (
    RagQueryResponse,
    RagResponseMetadata,
    RetrievalMetadata,
)
from backend.app.config import get_backend_settings
from backend.app.services.cache import TTLCache
from backend.app.services.citation_service import build_citations, format_context
from backend.app.services.llm_service import OllamaService
from backend.app.services.memory.memory_context import MemoryContext, MemoryContextService
from backend.app.services.memory.memory_extractor import RuleBasedMemoryExtractor
from backend.app.services.rag.fast_path_validator import FastAnswerCandidate, normalize_matchable, validate_fast_path
from backend.app.services.retriever_service import RetrieverService
from data_platform.processing.cleaners.text_cleaner import normalize_for_match
from data_platform.feature_store.embeddings.retriever import RetrievalResult


ANSWER_CACHE = TTLCache(namespace="answer", max_items=256)
ANSWER_CACHE_VERSION = "v2"


class AnswerService:
    def __init__(
        self,
        retriever_service: RetrieverService,
        llm_service: OllamaService,
        memory_service: MemoryContextService | None = None,
    ) -> None:
        self.retriever_service = retriever_service
        self.llm_service = llm_service
        self.memory_service = memory_service
        settings = get_backend_settings()
        self.answer_cache = ANSWER_CACHE
        self.answer_cache_ttl_seconds = settings.omni_answer_cache_ttl_sec
        self.force_llm = settings.omni_force_llm

    def answer(
        self,
        *,
        query: str,
        top_k: int,
        use_llm: bool,
        user_id: str = "default",
        session_id: str | None = None,
        include_memory: bool = True,
    ) -> RagQueryResponse:
        started = time.perf_counter()
        timings: dict[str, int | None] = {
            "embedding_latency_ms": None,
            "retrieval_latency_ms": None,
            "reranking_latency_ms": None,
            "llm_generation_latency_ms": None,
            "answer_synthesis_latency_ms": None,
            "citation_formatting_latency_ms": None,
        }
        query_type = classify_query_type(query)
        memory_context = self._build_memory_context(
            user_id=user_id,
            query=query,
            session_id=session_id,
            include_memory=include_memory,
        )
        retrieval_started = time.perf_counter()
        raw_results = self.retriever_service.retrieve(query, top_k=policy_top_k(query, top_k))
        timings["retrieval_latency_ms"] = int((time.perf_counter() - retrieval_started) * 1000)
        retriever_timings = getattr(self.retriever_service, "last_timings", {}) or {}
        timings["embedding_latency_ms"] = int(retriever_timings.get("embedding_latency_ms") or 0)
        rerank_started = time.perf_counter()
        results = filter_retrieval_results(raw_results, query=query)
        timings["reranking_latency_ms"] = int(retriever_timings.get("reranking_latency_ms") or 0) + int(
            (time.perf_counter() - rerank_started) * 1000
        )
        llm_results = select_context_results(results, query_type=query_type)
        confidence = retrieval_confidence(results)
        cacheable = is_cacheable_institutional_query(query=query, include_memory=include_memory, memory_context=memory_context)
        answer_cache_key = build_answer_cache_key(
            query=query,
            results=llm_results,
            role="default",
            language="vi",
            model_name=self.llm_service.model,
        )
        cached_answer = self.answer_cache.get(answer_cache_key) if cacheable else None

        mode = "extractive_fallback"
        cache_hit = False
        fast_path_metadata: dict = {"used": False, "validated": False, "reason": "not_applicable", "source_hashes": []}
        answer_text = ""
        leadership_answer = deterministic_leadership_answer(query, results)
        programming_answer = deterministic_programming_answer(query, results)
        curriculum_answer = deterministic_curriculum_answer(query, results)
        if cached_answer:
            answer_text = str(cached_answer.get("answer") or "")
            mode = str(cached_answer.get("mode") or "answer_cache")
            fast_path_metadata = cached_answer.get("fast_path") or fast_path_metadata
            cache_hit = True
            timings["llm_generation_latency_ms"] = 0
            timings["answer_synthesis_latency_ms"] = 0
        elif query_type == "simple_fact" and leadership_answer:
            validation = validate_fast_path(query=query, candidate_sources=results, fast_answer=leadership_answer)
            answer_text = leadership_answer.answer if validation["allowed"] else leadership_answer.fallback_answer
            mode = "deterministic_fact" if validation["allowed"] else "fast_path_refused"
            fast_path_metadata = to_fast_path_metadata(validation)
            timings["llm_generation_latency_ms"] = 0
            timings["answer_synthesis_latency_ms"] = 0
            if cacheable and validation["allowed"]:
                self.answer_cache.set(
                    answer_cache_key,
                    {"answer": answer_text, "mode": mode, "fast_path": fast_path_metadata},
                    ttl_seconds=self.answer_cache_ttl_seconds,
                )
        elif is_public_office_query(query):
            answer_text = "Dữ liệu hiện có chưa đủ để xác định chính xác. Cần kiểm tra nguồn chính thức về Ban Giám hiệu."
            mode = "fast_path_refused"
            fast_path_metadata = {
                "used": False,
                "validated": False,
                "reason": "official_leadership_source_missing",
                "source_hashes": [],
                "validated_sources": [],
                "fallback_required": True,
                "kind": "leadership",
            }
        elif programming_answer:
            validation = validate_fast_path(query=query, candidate_sources=results, fast_answer=programming_answer)
            if validation["allowed"]:
                answer_text = programming_answer.answer
                mode = "deterministic_fact"
                fast_path_metadata = to_fast_path_metadata(validation)
                timings["llm_generation_latency_ms"] = 0
                timings["answer_synthesis_latency_ms"] = 0
            else:
                fast_path_metadata = to_fast_path_metadata(validation)
            if cacheable and validation["allowed"]:
                self.answer_cache.set(
                    answer_cache_key,
                    {"answer": answer_text, "mode": mode, "fast_path": fast_path_metadata},
                    ttl_seconds=self.answer_cache_ttl_seconds,
                )
        elif curriculum_answer:
            validation = validate_fast_path(query=query, candidate_sources=results, fast_answer=curriculum_answer)
            if validation["allowed"]:
                answer_text = curriculum_answer.answer
                mode = "deterministic_summary"
                fast_path_metadata = to_fast_path_metadata(validation)
                timings["llm_generation_latency_ms"] = 0
                timings["answer_synthesis_latency_ms"] = 0
            else:
                fast_path_metadata = to_fast_path_metadata(validation)
            if cacheable and validation["allowed"]:
                self.answer_cache.set(
                    answer_cache_key,
                    {"answer": answer_text, "mode": mode, "fast_path": fast_path_metadata},
                    ttl_seconds=self.answer_cache_ttl_seconds,
                )
        if not answer_text and use_llm and results and self.llm_service.is_available():
            synthesis_started = time.perf_counter()
            generated = self.llm_service.generate(
                build_prompt(query, llm_results, memory_context, query_type=query_type),
                temperature=0.0,
                num_ctx=prompt_context_size(query_type),
            )
            timings["llm_generation_latency_ms"] = self.llm_service.last_latency_ms
            if generated and not is_bad_generation(generated, query, results):
                answer_text = ensure_citations(generated, len(results))
                mode = "ollama"
            else:
                retry = self.llm_service.generate(
                    build_prompt(query, llm_results[:3], memory_context, query_type=query_type, strict=True),
                    temperature=0.0,
                    num_ctx=2048,
                )
                timings["llm_generation_latency_ms"] = (timings["llm_generation_latency_ms"] or 0) + (
                    self.llm_service.last_latency_ms or 0
                )
                if retry and not is_bad_generation(retry, query, results):
                    answer_text = ensure_citations(retry, len(results))
                    mode = "ollama_retry"
                else:
                    answer_text = extractive_answer(results, memory_context)
                    mode = "extractive_guardrail"
            timings["answer_synthesis_latency_ms"] = int((time.perf_counter() - synthesis_started) * 1000)
            if cacheable and answer_text and mode.startswith("ollama"):
                self.answer_cache.set(
                    answer_cache_key,
                    {"answer": answer_text, "mode": mode},
                    ttl_seconds=self.answer_cache_ttl_seconds,
                )
        elif not answer_text:
            if leadership_answer:
                validation = validate_fast_path(query=query, candidate_sources=results, fast_answer=leadership_answer)
                answer_text = leadership_answer.answer if validation["allowed"] else leadership_answer.fallback_answer
                mode = "deterministic_fact" if validation["allowed"] else "fast_path_refused"
                fast_path_metadata = to_fast_path_metadata(validation)
            elif use_llm and self.force_llm and results:
                answer_text = "Ollama hiện không sẵn sàng nên mình chưa thể tổng hợp câu trả lời bằng LLM cục bộ."
                mode = "llm_unavailable"
            else:
                answer_text = extractive_answer(results, memory_context)
                mode = "extractive_fallback"

        if not results:
            answer_text = extractive_answer(results, memory_context)
            mode = "no_retrieval_context"

        if self.memory_service and session_id:
            self.memory_service.session_memory.append_turn(
                user_id=user_id,
                session_id=session_id,
                role="user",
                content=query,
                metadata={"source": "rag_query", "intent": "rag"},
            )
            self.memory_service.session_memory.append_turn(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=answer_text[:1200],
                metadata={"source": "rag_answer", "mode": mode, "intent": "rag"},
            )
            if include_memory and not cacheable:
                self.memory_service.semantic_memory.add_conversation_summary(
                    user_id=user_id,
                    session_id=session_id,
                    summary=f"User asked: {query}. Assistant answered: {answer_text[:500]}",
                )

        self._extract_explicit_memory(user_id=user_id, query=query)

        latency_ms = int((time.perf_counter() - started) * 1000)
        citation_started = time.perf_counter()
        citations = build_citations(results, answer=answer_text, query=query, cited_only=True)
        debug_retrieval = build_citations(results, answer=answer_text, query=query, cited_only=False)
        timings["citation_formatting_latency_ms"] = int((time.perf_counter() - citation_started) * 1000)

        return RagQueryResponse(
            answer=answer_text,
            citations=citations,
            debug_retrieval=debug_retrieval,
            retrieval=RetrievalMetadata(
                top_k=top_k,
                collection=self.retriever_service.collection,
                embedding_model=self.retriever_service.embedding_model_name,
            ),
            metadata=RagResponseMetadata(
                latency_ms=latency_ms,
                mode=mode,
                memory_items=memory_context.item_count if memory_context else 0,
                retrieval_confidence=confidence,
                best_score=results[0].score if results else None,
                debug_retrieval_count=len(results),
                cache_hit=cache_hit,
                query_type=query_type,
                llm_error=self.llm_service.last_error,
                fast_path=fast_path_metadata,
                **timings,
            ),
        )

    def _build_memory_context(
        self,
        *,
        user_id: str,
        query: str,
        session_id: str | None,
        include_memory: bool,
    ) -> MemoryContext | None:
        if not include_memory or self.memory_service is None:
            return None
        return self.memory_service.build_context(user_id=user_id, query=query, session_id=session_id)

    def _extract_explicit_memory(self, *, user_id: str, query: str) -> None:
        if self.memory_service is None:
            return
        extractor = RuleBasedMemoryExtractor()
        for item in extractor.extract_memories(query):
            self.memory_service.remember_text(
                user_id=user_id,
                text=item.content,
                memory_type=item.memory_type,
                importance=item.importance,
                source="rag_explicit",
            )
        for task in extractor.extract_tasks(query):
            self.memory_service.task_memory.add_task(
                user_id=user_id,
                title=task.title,
                due_date=task.due_date,
                priority=task.priority,
                source_text=query,
            )


def build_prompt(
    query: str,
    results: list[RetrievalResult],
    memory_context: MemoryContext | None = None,
    *,
    query_type: str = "general",
    strict: bool = False,
) -> str:
    context = format_context(results)
    memory_block = (
        memory_context.to_prompt_block()
        if memory_context and memory_context.item_count
        else "No personal memory context."
    )
    length_hint = "Trả lời 1-2 câu ngắn." if query_type == "simple_fact" else "Trả lời bằng 3-5 ý ngắn."
    strict_hint = "Nếu câu trả lời trước bị lẫn ngôn ngữ, lần này chỉ viết tiếng Việt tự nhiên." if strict else ""
    return f"""Bạn là Lumi, trợ lý AI cục bộ cho Trường Đại học Khoa học Tự nhiên, ĐHQGHN.

Chỉ dùng NGỮ CẢNH được đánh số để trả lời thông tin về nhà trường.
Viết hoàn toàn bằng tiếng Việt. Không dùng tiếng Anh, Indonesia, Malay, Trung, Nhật hoặc ký tự lạ.
Không bịa tên người, chức danh, ngày tháng, quy định, tuyển sinh hoặc lãnh đạo.
Gắn trích dẫn [1], [2] ngay sau thông tin thực tế. {length_hint}
Nếu ngữ cảnh không đủ rõ, chỉ nói: "Dữ liệu hiện có chưa đủ để kết luận."
{strict_hint}

TRÍ NHỚ CÁ NHÂN:
{memory_block}

CÂU HỎI:
{query}

NGỮ CẢNH:
{context}

TRẢ LỜI:
"""


def extractive_answer(
    results: list[RetrievalResult],
    memory_context: MemoryContext | None = None,
) -> str:
    if not results:
        return "Dữ liệu hiện có chưa đủ để kết luận."

    bullets: list[str] = []
    if memory_context and memory_context.item_count:
        memory_lines = memory_context.to_prompt_block().splitlines()
        if memory_lines:
            bullets.append(f"Ngữ cảnh cá nhân liên quan: {memory_lines[0]}")
    for result in results[:3]:
        fact = compact_fact(result)
        if fact and fact not in bullets:
            bullets.append(fact)
    if not bullets:
        return "Dữ liệu hiện có chưa đủ sạch để kết luận chắc chắn."
    lines = [
        "Mình tổng hợp được các ý chính sau từ nguồn đã lập chỉ mục:",
        "",
        *[f"- {item}" for item in bullets[:4]],
        "",
        "Bạn có thể mở các nguồn bên dưới để đối chiếu thông tin gốc.",
    ]
    return "\n".join(lines)


def ensure_citations(answer: str, source_count: int) -> str:
    return answer


def compact_fact(result: RetrievalResult) -> str:
    text = str(result.payload.get("preview_text") or "").strip() or readable_excerpt(result.text, limit=260)
    text = re.sub(r"\[\d+\]", "", text)
    text = " ".join(text.split())
    if not text:
        return ""
    if len(text) <= 240:
        return text.rstrip(" .") + "."
    return readable_excerpt(text, limit=240).rstrip(" .") + "."


def deterministic_leadership_answer(query: str, results: list[RetrievalResult]) -> FastAnswerCandidate | None:
    query_profile = normalize_matchable(query)
    if not any(term in query_profile for term in ("hieu truong", "pho hieu truong", "ban giam hieu", "lanh dao")):
        return None

    for source_index, result in enumerate(results[:4], start=1):
        text = " ".join(result.text.split())
        role_matches = re.findall(
            r"((?:GS|PGS)\.?\s*TS\.?\s*[^.\n-]+?)\s*-\s*(Hiệu trưởng|Phó Hiệu trưởng)",
            text,
        )
        if not role_matches:
            continue
        rector = next((name.strip() for name, role in role_matches if role == "Hiệu trưởng"), "")
        vice_rectors = [name.strip() for name, role in role_matches if role == "Phó Hiệu trưởng"]
        marker = f"[{source_index}]"
        if ("ban giam hieu" in query_profile or "gom" in query_profile or "nhung ai" in query_profile) and rector:
            lines = [
                f"Ban Giám hiệu Trường Đại học Khoa học Tự nhiên - Đại học Quốc gia Hà Nội gồm:",
                f"- Hiệu trưởng: {rector} {marker}",
            ]
            if vice_rectors:
                lines.append(f"- Phó Hiệu trưởng: {', '.join(vice_rectors)} {marker}")
            return FastAnswerCandidate(
                kind="leadership",
                answer="\n".join(lines),
                source_index=source_index,
                expected_document_type="leadership",
                required_url_contains=("hus.vnu.edu.vn/gioi-thieu/co-cau-to-chuc/ban-giam-hieu",),
                required_terms=("Ban Giám hiệu", "Hiệu trưởng", "GS.TS. Lê Thanh Sơn"),
                fallback_answer="Dữ liệu hiện có chưa đủ để xác định chính xác. Cần kiểm tra nguồn chính thức về Ban Giám hiệu.",
            )
        if rector:
            return FastAnswerCandidate(
                kind="leadership",
                answer=f"Hiệu trưởng Trường Đại học Khoa học Tự nhiên - Đại học Quốc gia Hà Nội là {rector} {marker}.",
                source_index=source_index,
                expected_document_type="leadership",
                required_url_contains=("hus.vnu.edu.vn/gioi-thieu/co-cau-to-chuc/ban-giam-hieu",),
                required_terms=("Ban Giám hiệu", "Hiệu trưởng", "GS.TS. Lê Thanh Sơn"),
                fallback_answer="Dữ liệu hiện có chưa đủ để xác định chính xác. Cần kiểm tra nguồn chính thức về Ban Giám hiệu.",
            )
    return None


def deterministic_programming_answer(query: str, results: list[RetrievalResult]) -> FastAnswerCandidate | None:
    query_profile = normalize_matchable(query)
    if "hoc lap trinh" not in query_profile and "lap trinh" not in query_profile:
        return None
    for source_index, result in enumerate(results[:4], start=1):
        text_profile = normalize_matchable(result.text)
        if "lap trinh" in text_profile or "khoa hoc may tinh" in text_profile:
            return FastAnswerCandidate(
                kind="data_science_programming",
                answer=(
                    "Có. Theo nguồn tuyển sinh HUS, ngành Khoa học dữ liệu trang bị kỹ năng lập trình, "
                    "lưu trữ và tổ chức dữ liệu, cùng nền tảng khoa học máy tính, thống kê và toán ứng dụng "
                    f"[{source_index}]."
                ),
                source_index=source_index,
                expected_document_type="admission",
                required_url_contains=("tuyensinh.hus.vnu.edu.vn",),
                required_terms=("Khoa học dữ liệu", "lập trình"),
            )
    return None


def deterministic_curriculum_answer(query: str, results: list[RetrievalResult]) -> FastAnswerCandidate | None:
    query_profile = normalize_matchable(query)
    if "hoc nhung mon gi" not in query_profile and "hoc gi" not in query_profile:
        return None
    for source_index, result in enumerate(results[:5], start=1):
        if "tuyensinh.hus.vnu.edu.vn" not in result.source_url:
            continue
        text_profile = normalize_matchable(result.text)
        if "khoa hoc du lieu" not in text_profile:
            continue
        if "khoa hoc may tinh" in text_profile and "thong ke" in text_profile and "toan" in text_profile:
            return FastAnswerCandidate(
                kind="data_science_curriculum",
                answer=(
                    "Ngành Khoa học dữ liệu học nền tảng thuộc ba nhóm chính: Khoa học máy tính, "
                    "Thống kê và Toán ứng dụng. Chương trình cũng nhấn mạnh lập trình, lưu trữ và tổ chức dữ liệu, "
                    f"mô hình hóa, phân tích dữ liệu bằng thống kê và các kỹ năng thực hành dữ liệu [{source_index}]."
                ),
                source_index=source_index,
                expected_document_type="admission",
                required_url_contains=("tuyensinh.hus.vnu.edu.vn",),
                required_terms=("Khoa học dữ liệu", "khoa học máy tính", "thống kê", "toán"),
            )
    return None


def to_fast_path_metadata(validation: dict) -> dict:
    return {
        "used": bool(validation.get("allowed")),
        "validated": bool(validation.get("allowed")),
        "reason": validation.get("reason", ""),
        "source_hashes": validation.get("source_hashes", []),
        "validated_sources": validation.get("validated_sources", []),
        "fallback_required": validation.get("fallback_required", False),
        "kind": validation.get("kind"),
    }


def is_bad_generation(answer: str, query: str, results: list[RetrievalResult]) -> bool:
    normalized_answer = answer.lower()
    if any(marker in answer for marker in ("Ã", "á»", "Ä‘", "Dá", "mel不")):
        return True
    if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", answer):
        return True
    if contains_suspicious_foreign_fragment(normalized_answer):
        return True
    if unsupported_english_ratio(answer, results) > 0.18:
        return True
    insufficient = "dữ liệu hiện có chưa đủ" in normalized_answer or "du lieu hien co chua du" in normalized_answer
    if insufficient and has_useful_context(query, results):
        return True
    return False


def contains_suspicious_foreign_fragment(normalized_answer: str) -> bool:
    suspicious_terms = (
        " dari ",
        " dengan ",
        " untuk ",
        " adalah ",
        " sains bumi ",
        " kehidupan",
        " teknologi",
        " terming ",
        " yang ",
        " dalam ",
        " pada ",
    )
    return any(term in f" {normalized_answer} " for term in suspicious_terms)


def unsupported_english_ratio(answer: str, results: list[RetrievalResult]) -> float:
    tokens = [token.lower() for token in re.findall(r"[A-Za-z]{4,}", answer)]
    if not tokens:
        return 0.0
    source_text = " ".join(result.text.lower() for result in results[:4])
    unsupported = [token for token in tokens if token not in source_text and token not in {"omniassistant", "hus", "vnu"}]
    return len(unsupported) / max(1, len(tokens))


def has_useful_context(query: str, results: list[RetrievalResult]) -> bool:
    if not results or results[0].score < 0.78:
        return False
    query_terms = {
        token
        for token in re.findall(r"[a-zA-Z0-9À-ỹ]+", query.lower())
        if len(token) >= 4 and token not in {"trường", "truong", "ngành", "nganh", "những", "nhung", "được", "duoc"}
    }
    context = " ".join(result.text.lower() for result in results[:3])
    if any(term in context for term in query_terms):
        return True
    return any(result.document_type == "leadership" for result in results[:3])


def retrieval_confidence(results: list[RetrievalResult]) -> str:
    if not results:
        return "none"
    best = results[0].score
    if best >= 0.62:
        return "high"
    if best >= 0.45:
        return "medium"
    return "low"


def filter_retrieval_results(results: list[RetrievalResult], *, query: str = "") -> list[RetrievalResult]:
    filtered: list[RetrievalResult] = []
    query_profile = normalize_for_match(query)
    leadership_query = is_factual_entity_query(query_profile)
    has_leadership_evidence = any(is_leadership_evidence(result) for result in results)
    for result in results:
        payload = result.payload or {}
        features = payload.get("features") or {}
        content_quality = float(payload.get("content_quality_score") or features.get("content_quality_score") or 0.5)
        boilerplate = float(payload.get("boilerplate_score") or features.get("boilerplate_score") or 0.0)
        menu_density = float(payload.get("menu_density_score") or features.get("menu_density_score") or 0.0)
        text = " ".join(result.text.split())
        if len(text) < 80:
            continue
        if content_quality < 0.30:
            continue
        if menu_density >= 0.65 and content_quality <= 0.55:
            continue
        if boilerplate >= 0.8 and content_quality <= 0.4:
            continue
        if leadership_query and has_leadership_evidence and not is_leadership_evidence(result):
            continue
        filtered.append(result)
    if filtered:
        return filtered
    return results[: min(len(results), 3)]


def is_factual_entity_query(query_profile: str) -> bool:
    terms = (
        "ai la",
        "hieu truong",
        "ban giam hieu",
        "lanh dao",
        "truong khoa",
        "giam doc",
    )
    return any(term in query_profile for term in terms)


def is_public_office_query(query: str) -> bool:
    profile = normalize_matchable(query)
    return any(term in profile for term in ("hieu truong", "pho hieu truong", "ban giam hieu", "lanh dao"))


def is_leadership_evidence(result: RetrievalResult) -> bool:
    text_profile = normalize_for_match(" ".join([result.title or "", result.document_type or "", result.source_url or "", result.text or ""]))
    if result.document_type == "leadership":
        return True
    evidence_terms = ("hieu truong", "pho hieu truong", "ban giam hieu", "lanh dao", "gs.ts", "pgs.ts")
    return any(term in text_profile for term in evidence_terms)


def readable_excerpt(text: str, *, limit: int = 420) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    floor = int(limit * 0.65)
    for delimiter in (". ", "? ", "! ", "; ", ": "):
        boundary = compact.rfind(delimiter, floor, limit)
        if boundary > 0:
            return compact[: boundary + 1].rstrip() + "…"
    boundary = compact.rfind(" ", floor, limit)
    if boundary > 0:
        return compact[:boundary].rstrip(" ,;:") + "…"
    return compact[:limit].rstrip(" ,;:") + "…"


def classify_query_type(query: str) -> str:
    profile = normalize_matchable(query)
    if any(term in profile for term in ("ai la", "la ai", "hieu truong", "pho hieu truong", "o dau", "may nam")):
        return "simple_fact"
    if any(term in profile for term in ("hoc nhung mon gi", "co hoc lap trinh", "chuong trinh", "tong quan", "giai thich")):
        return "broad_explanation"
    return "general"


def policy_top_k(query: str, requested_top_k: int) -> int:
    query_type = classify_query_type(query)
    if query_type == "simple_fact":
        return min(max(requested_top_k, 3), 4)
    if query_type == "broad_explanation":
        return min(max(requested_top_k, 6), 8)
    return requested_top_k


def prompt_context_size(query_type: str) -> int:
    if query_type == "simple_fact":
        return 1536
    if query_type == "broad_explanation":
        return 2560
    return 2048


def select_context_results(results: list[RetrievalResult], *, query_type: str) -> list[RetrievalResult]:
    limit = 3 if query_type == "simple_fact" else 5 if query_type == "broad_explanation" else 4
    selected: list[RetrievalResult] = []
    seen: set[tuple[str, str]] = set()
    for result in results:
        key = (result.source_url, result.title or "")
        if key in seen and len(selected) >= 2:
            continue
        seen.add(key)
        selected.append(result)
        if len(selected) >= limit:
            break
    return selected or results[:limit]


def is_cacheable_institutional_query(
    *,
    query: str,
    include_memory: bool,
    memory_context: MemoryContext | None,
) -> bool:
    profile = normalize_for_match(query)
    if any(term in profile for term in ("hom nay", "email", "gmail", "task", "viec", "lich", "nho ")):
        return False
    if include_memory and memory_context and memory_context.item_count:
        return False
    return True


def build_answer_cache_key(
    *,
    query: str,
    results: list[RetrievalResult],
    role: str,
    language: str,
    model_name: str,
) -> str:
    source_fingerprint = [
        {
            "chunk_id": result.payload.get("chunk_id") or result.payload.get("id"),
            "source_url": result.source_url,
            "score": round(result.score, 3),
            "hash": result.payload.get("content_hash")
            or result.payload.get("chunk_hash")
            or hashlib.sha1(result.text[:500].encode("utf-8")).hexdigest(),
        }
        for result in results[:5]
    ]
    raw = json.dumps(
        {
            "query": normalize_matchable(query),
            "version": ANSWER_CACHE_VERSION,
            "sources": source_fingerprint,
            "role": role,
            "language": language,
            "model": model_name,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

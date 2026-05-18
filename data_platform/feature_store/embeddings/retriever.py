"""Semantic chunk retrieval from Qdrant."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

from data_platform.feature_store.embeddings.embedding_model import LocalEmbeddingModel
from data_platform.feature_store.embeddings.qdrant_client_factory import create_qdrant_client
from data_platform.processing.cleaners.text_cleaner import normalize_for_match

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalResult:
    title: str | None
    document_type: str
    score: float
    vector_score: float
    source_url: str
    text: str
    payload: dict[str, Any]


class QdrantRetriever:
    def __init__(
        self,
        *,
        qdrant_url: str,
        collection_name: str,
        embedding_model: LocalEmbeddingModel,
        local_path: Any = None,
    ) -> None:
        self.client = create_qdrant_client(qdrant_url=qdrant_url, local_path=local_path)
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.last_timings: dict[str, int] = {}
        if local_path is not None and not collection_exists(self.client, collection_name):
            logger.warning(
                "Qdrant collection %s is missing on configured server. Falling back to local path %s",
                collection_name,
                local_path,
            )
            from qdrant_client import QdrantClient

            Path(local_path).mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(local_path))

    def retrieve(self, query: str, *, top_k: int = 5, candidate_k: int | None = None) -> list[RetrievalResult]:
        import time

        started = time.perf_counter()
        query_vector = self.embedding_model.embed_query(query)
        embedding_latency_ms = int((time.perf_counter() - started) * 1000)
        limit = candidate_k or max(top_k * 4, top_k)
        qdrant_started = time.perf_counter()
        if hasattr(self.client, "search"):
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
        else:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            hits = response.points
        qdrant_latency_ms = int((time.perf_counter() - qdrant_started) * 1000)
        rerank_started = time.perf_counter()
        query_profile = normalize_for_match(query)
        reranked = [to_result(hit, query_profile=query_profile) for hit in hits]
        reranked.sort(key=lambda item: item.score, reverse=True)
        reranked = apply_query_specific_filters(query_profile, reranked)
        self.last_timings = {
            "embedding_latency_ms": embedding_latency_ms,
            "qdrant_latency_ms": qdrant_latency_ms,
            "reranking_latency_ms": int((time.perf_counter() - rerank_started) * 1000),
        }
        return reranked[:top_k]


def to_result(hit: Any, *, query_profile: str = "") -> RetrievalResult:
    payload = hit.payload or {}
    vector_score = float(hit.score or 0.0)
    authority = float(payload.get("authority_score") or 0.0)
    freshness = float(payload.get("freshness_score") or 0.0)
    content_quality = float(payload.get("content_quality_score") or 0.5)
    boilerplate = float(payload.get("boilerplate_score") or 0.0)
    final_score = (
        vector_score * 0.70
        + authority * 0.10
        + freshness * 0.05
        + content_quality * 0.15
        - boilerplate * 0.20
        + query_type_boost(query_profile, payload)
    )
    return RetrievalResult(
        title=payload.get("title"),
        document_type=str(payload.get("document_type") or "unknown"),
        score=round(max(0.0, final_score), 6),
        vector_score=round(vector_score, 6),
        source_url=str(payload.get("source_url") or ""),
        text=str(payload.get("text") or ""),
        payload=payload,
    )


def query_type_boost(query_profile: str, payload: dict[str, Any]) -> float:
    document_type = str(payload.get("document_type") or "unknown")
    source_url = normalize_for_match(str(payload.get("source_url") or ""))
    title = normalize_for_match(str(payload.get("title") or ""))
    text = normalize_for_match(str(payload.get("text") or "")[:600])

    if is_leadership_query(query_profile):
        exact_evidence = any(
            term in f"{title} {source_url} {text}"
            for term in ("ban giam hieu", "hieu truong", "pho hieu truong", "lanh dao", "gs.ts", "pgs.ts")
        )
        if document_type == "leadership":
            return 0.22
        if exact_evidence and "hus.vnu.edu.vn" in source_url:
            return 0.10
        if document_type in {"admission", "announcement", "program", "curriculum"}:
            return -0.18
        if "lich su" in title and "ban giam hieu" not in text:
            return -0.12

    if any(term in query_profile for term in ("khoa hoc du lieu", "khoa hoc may tinh", "nganh", "chuong trinh dao tao")):
        if "tuyensinh.hus.vnu.edu.vn" in source_url or document_type in {"admission", "curriculum", "program"}:
            return 0.04
        if document_type in {"general_info", "department", "quality_assurance"}:
            return -0.04

    if any(term in query_profile for term in ("danh sach can bo", "giang vien", "can bo")):
        if document_type == "lecturer_profile" or "can-bo" in source_url:
            return 0.08
        if document_type == "leadership" and "ban giam hieu" not in query_profile:
            return -0.04

    if any(term in query_profile for term in ("khoa truc thuoc", "phong dao tao", "phong ban", "lien he")):
        if document_type == "department" or contains_any(f"{title} {source_url} {text}", ("khoa truc thuoc", "phong ban chuc nang", "phong dao tao")):
            return 0.16
        if document_type in {"admission", "announcement", "regulation"}:
            return -0.08

    if any(term in query_profile for term in ("dam bao chat luong", "ba cong khai")):
        if document_type == "quality_assurance" or contains_any(f"{title} {source_url} {text}", ("dam bao chat luong", "ba cong khai")):
            return 0.16

    if any(term in query_profile for term in ("su mang", "tam nhin", "lich su", "phat trien")):
        if document_type == "general_info":
            return 0.08

    if "lich su" in query_profile and "lich-su-phat-trien" in source_url:
        return 0.06

    if "phong dao tao" in query_profile and "phong-dao-tao" in source_url:
        return 0.1

    return 0.0


def contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def apply_query_specific_filters(
    query_profile: str,
    results: list[RetrievalResult],
) -> list[RetrievalResult]:
    if not is_leadership_query(query_profile):
        return results

    current_leadership = [result for result in results if is_current_leadership_result(result)]
    if current_leadership:
        current_leadership.sort(key=lambda item: item.score, reverse=True)
        return current_leadership

    evidence = [result for result in results if is_leadership_result(result)]
    if not evidence:
        return results

    evidence.sort(key=lambda item: item.score, reverse=True)
    return evidence


def is_leadership_query(query_profile: str) -> bool:
    return any(
        term in query_profile
        for term in (
            "ai la",
            "hieu truong",
            "pho hieu truong",
            "ban giam hieu",
            "lanh dao",
            "truong khoa",
            "giam doc",
        )
    )


def is_leadership_result(result: RetrievalResult) -> bool:
    haystack = normalize_for_match(
        " ".join(
            [
                result.document_type,
                result.title or "",
                result.source_url,
                result.text[:1000],
            ]
        )
    )
    if is_current_leadership_result(result):
        return True
    if "https://hus.vnu.edu.vn" not in result.source_url:
        return False
    return any(
        term in haystack
        for term in (
            "ban giam hieu",
            "hieu truong",
            "pho hieu truong",
            "lanh dao",
            "gs.ts",
            "pgs.ts",
        )
    )


def is_current_leadership_result(result: RetrievalResult) -> bool:
    haystack = normalize_for_match(
        " ".join(
            [
                result.document_type,
                result.title or "",
                result.source_url,
            ]
        )
    )
    return result.document_type == "leadership" or "ban-giam-hieu" in haystack


def collection_exists(client: Any, collection_name: str) -> bool:
    try:
        collections = client.get_collections().collections
        return any(collection.name == collection_name for collection in collections)
    except Exception:
        return False

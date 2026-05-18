"""Source-bound validation for deterministic RAG fast paths."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from data_platform.feature_store.embeddings.retriever import RetrievalResult


@dataclass(frozen=True)
class FastAnswerCandidate:
    kind: str
    answer: str
    source_index: int
    required_terms: tuple[str, ...]
    expected_document_type: str | None = None
    required_url_contains: tuple[str, ...] = ()
    fallback_answer: str = "Dữ liệu hiện có chưa đủ để kết luận."


def validate_fast_path(
    *,
    query: str,
    candidate_sources: list[RetrievalResult],
    fast_answer: FastAnswerCandidate | None,
) -> dict[str, Any]:
    if fast_answer is None:
        return {
            "allowed": False,
            "reason": "no_fast_answer_candidate",
            "validated_sources": [],
            "source_hashes": [],
            "fallback_required": True,
        }

    if fast_answer.source_index < 1 or fast_answer.source_index > len(candidate_sources):
        return denied("source_index_out_of_range")

    source = candidate_sources[fast_answer.source_index - 1]
    payload = source.payload or {}
    chunk_id = payload.get("chunk_id") or payload.get("id")
    if not chunk_id:
        return denied("chunk_id_missing")

    if fast_answer.expected_document_type and source.document_type != fast_answer.expected_document_type:
        return denied(f"document_type_mismatch:{source.document_type}")

    source_url = source.source_url or ""
    for required_url in fast_answer.required_url_contains:
        if required_url not in source_url:
            return denied(f"source_url_missing:{required_url}")

    source_text = normalize_matchable(" ".join([source.title or "", source.document_type, source_url, source.text]))
    missing_terms = [term for term in fast_answer.required_terms if normalize_matchable(term) not in source_text]
    if missing_terms:
        return denied(f"missing_evidence:{','.join(missing_terms)}")

    source_hash = source_hash_for(source)
    validated_source = {
        "title": source.title,
        "source_url": source.source_url,
        "document_type": source.document_type,
        "chunk_id": chunk_id,
        "source_hash": source_hash,
        "score": source.score,
        "citation_index": fast_answer.source_index,
    }
    return {
        "allowed": True,
        "reason": f"{fast_answer.kind}_validated",
        "validated_sources": [validated_source],
        "source_hashes": [source_hash],
        "fallback_required": False,
        "kind": fast_answer.kind,
        "query": query,
    }


def denied(reason: str) -> dict[str, Any]:
    return {
        "allowed": False,
        "reason": reason,
        "validated_sources": [],
        "source_hashes": [],
        "fallback_required": True,
    }


def source_hash_for(source: RetrievalResult) -> str:
    payload = source.payload or {}
    for key in ("content_hash", "chunk_hash", "source_hash"):
        value = payload.get(key)
        if value:
            return str(value)
    fingerprint = "|".join(
        [
            source.source_url or "",
            source.document_type or "",
            str(payload.get("chunk_id") or payload.get("id") or ""),
            " ".join((source.text or "").split())[:1200],
        ]
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def normalize_matchable(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    text = re.sub(r"\s+", " ", text).lower().strip()
    return text


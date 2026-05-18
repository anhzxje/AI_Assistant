"""Rule-based answer quality diagnostics."""

from __future__ import annotations

import re
from typing import Any

from backend.app.services.quality.retrieval_diagnostics import (
    has_very_low_scores,
    repeated_source_issues,
    retrieval_scores,
)
from orchestration.intent_classifier_v2 import is_institutional_query
from orchestration.assistant_brain import normalize_text


CITATION_RE = re.compile(r"\[\d+\]")
RAG_INTENTS = {"institutional_rag", "rag"}


def diagnose_answer(
    *,
    query: str,
    answer: str,
    intent: str,
    sources: list[dict[str, Any]],
    metadata: dict[str, Any],
    latency_ms: int,
) -> dict[str, Any]:
    issues: list[str] = []
    normalized_query = normalize_text(query)
    normalized_answer = normalize_text(answer)

    if intent in RAG_INTENTS and not sources:
        issues.append("rag_intent_without_sources")
    if has_very_low_scores(sources):
        issues.append("very_low_retrieval_scores")
    # Source cards carry the citation contract. Inline [1] markers are optional
    # so user-facing answers can stay readable and avoid source dumps.
    if len(answer.strip()) < 40:
        issues.append("answer_too_short")
    if "du lieu hien co chua du" in normalized_answer or "insufficient" in normalized_answer:
        issues.append("insufficient_data_answer")
    if is_institutional_query(normalized_query) and intent not in RAG_INTENTS:
        issues.append("hus_query_not_routed_to_institutional_rag")
    if intent == "general_chat" and metadata.get("general_llm_mode") == "disabled":
        issues.append("general_chat_llm_disabled")
    if latency_ms > 8000:
        issues.append("latency_too_high")
    issues.extend(repeated_source_issues(sources))

    quality_score = score_quality(issues)
    return {
        "quality_score": quality_score,
        "issues": issues,
        "suggested_feedback_reason": suggested_feedback_reason(issues),
        "requires_admin_review": requires_admin_review(issues),
        "diagnostics": {
            "source_count": len(sources),
            "has_citations": bool(CITATION_RE.search(answer)),
            "latency_ms": latency_ms,
            "retrieval_scores": retrieval_scores(sources),
            "suspected_issue": issues[0] if issues else "",
        },
    }


def score_quality(issues: list[str]) -> float:
    score = 1.0
    weights = {
        "rag_intent_without_sources": 0.4,
        "very_low_retrieval_scores": 0.25,
        "answer_too_short": 0.15,
        "insufficient_data_answer": 0.15,
        "hus_query_not_routed_to_institutional_rag": 0.35,
        "general_chat_llm_disabled": 0.1,
        "latency_too_high": 0.15,
    }
    for issue in issues:
        if issue.startswith("source_repeated:"):
            score -= 0.15
        else:
            score -= weights.get(issue, 0.1)
    return round(max(0.0, min(1.0, score)), 4)


def suggested_feedback_reason(issues: list[str]) -> str:
    if "rag_intent_without_sources" in issues:
        return "missing_source"
    if "hus_query_not_routed_to_institutional_rag" in issues:
        return "irrelevant_retrieval"
    if "very_low_retrieval_scores" in issues or any(issue.startswith("source_repeated:") for issue in issues):
        return "irrelevant_retrieval"
    if "latency_too_high" in issues:
        return "too_slow"
    return "other"


def requires_admin_review(issues: list[str]) -> bool:
    serious = {
        "rag_intent_without_sources",
        "very_low_retrieval_scores",
        "hus_query_not_routed_to_institutional_rag",
    }
    return any(issue in serious or issue.startswith("source_repeated:") for issue in issues)

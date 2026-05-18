"""Lightweight groundedness evaluation for RAG answers."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from backend.app.schemas.rag_schema import RagQueryRequest
from backend.app.services.answer_service import AnswerService
from backend.app.services.llm_service import OllamaService
from backend.app.services.retriever_service import get_retriever_service

CITATION_RE = re.compile(r"\[\d+\]")


def evaluate_rag_groundedness(eval_path: Path, *, top_k: int = 5, use_llm: bool = False) -> dict[str, Any]:
    cases = read_jsonl(eval_path)
    answer_service = AnswerService(get_retriever_service(), OllamaService())
    results: list[dict[str, Any]] = []
    scores: list[float] = []
    latencies: list[int] = []

    for case in cases:
        started = time.perf_counter()
        response = answer_service.answer(query=str(case["query"]), top_k=top_k, use_llm=use_llm)
        latency_ms = int((time.perf_counter() - started) * 1000)
        latencies.append(latency_ms)

        groundedness = score_groundedness(response.answer, [citation.preview for citation in response.citations])
        scores.append(groundedness["score"])
        results.append(
            {
                "query": case["query"],
                "mode": response.metadata.mode,
                "latency_ms": response.metadata.latency_ms,
                "citations_count": len(response.citations),
                "groundedness": groundedness,
                "answer_preview": response.answer[:500],
            }
        )

    total = len(results)
    citation_pass_rate = sum(1 for item in results if item["groundedness"]["has_citation_marker"]) / total if total else 0.0
    return {
        "total_cases": total,
        "top_k": top_k,
        "use_llm": use_llm,
        "average_groundedness_score": round(sum(scores) / total, 4) if total else 0.0,
        "citation_marker_pass_rate": round(citation_pass_rate, 4),
        "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "results": results,
    }


def score_groundedness(answer: str, context_previews: list[str]) -> dict[str, Any]:
    answer_lower = answer.lower()
    context_lower = " ".join(context_previews).lower()
    answer_tokens = meaningful_tokens(answer_lower)
    context_tokens = set(meaningful_tokens(context_lower))
    overlap = [token for token in answer_tokens if token in context_tokens]
    overlap_rate = len(set(overlap)) / len(set(answer_tokens)) if answer_tokens else 0.0
    has_citation = bool(CITATION_RE.search(answer))
    non_empty = bool(answer.strip())
    says_insufficient = "dữ liệu hiện có chưa đủ" in answer_lower

    score = 0.0
    score += 0.25 if non_empty else 0.0
    score += 0.25 if has_citation else 0.0
    score += min(overlap_rate, 0.4)
    score += 0.10 if says_insufficient else 0.0
    return {
        "score": round(min(score, 1.0), 4),
        "has_citation_marker": has_citation,
        "non_empty": non_empty,
        "context_token_overlap_rate": round(overlap_rate, 4),
        "says_insufficient": says_insufficient,
    }


def meaningful_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[\wÀ-ỹ]+", text.lower()) if len(token) >= 4]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

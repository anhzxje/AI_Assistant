"""Retrieval evaluation over seed Vietnamese QA cases."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from backend.app.services.retriever_service import get_retriever_service


def evaluate_retrieval(eval_path: Path, *, top_k: int = 5) -> dict[str, Any]:
    cases = read_jsonl(eval_path)
    retriever = get_retriever_service()
    results: list[dict[str, Any]] = []
    type_hits = 0
    keyword_rates: list[float] = []
    scores: list[float] = []
    latencies: list[int] = []

    for case in cases:
        if str(case.get("status") or "").lower() in {"ignored", "skip"}:
            results.append(
                {
                    "query": case["query"],
                    "expected_document_type": str(case.get("expected_document_type") or ""),
                    "type_hit": None,
                    "skipped": True,
                    "skip_reason": case.get("skip_reason") or "ignored_case",
                    "keyword_hit_rate": 0.0,
                    "latency_ms": 0,
                    "top_results": [],
                }
            )
            continue
        started = time.perf_counter()
        retrieved = retriever.retrieve(str(case["query"]), top_k=top_k)
        latency_ms = int((time.perf_counter() - started) * 1000)
        latencies.append(latency_ms)

        expected_type = str(case.get("expected_document_type") or "")
        type_hit = any(item.document_type == expected_type for item in retrieved)
        type_hits += int(type_hit)

        expected_keywords = [str(keyword).lower() for keyword in case.get("expected_keywords", [])]
        combined_text = " ".join(
            f"{item.title or ''} {item.text}" for item in retrieved
        ).lower()
        keyword_hit_count = sum(1 for keyword in expected_keywords if keyword in combined_text)
        keyword_rate = keyword_hit_count / len(expected_keywords) if expected_keywords else 1.0
        keyword_rates.append(keyword_rate)

        query_scores = [item.score for item in retrieved]
        scores.extend(query_scores)

        results.append(
            {
                "query": case["query"],
                "expected_document_type": expected_type,
                "type_hit": type_hit,
                "keyword_hit_rate": round(keyword_rate, 4),
                "latency_ms": latency_ms,
                "top_results": [
                    {
                        "title": item.title,
                        "document_type": item.document_type,
                        "score": item.score,
                        "source_url": item.source_url,
                    }
                    for item in retrieved
                ],
            }
        )

    evaluated = [result for result in results if not result.get("skipped")]
    total = len(evaluated)
    return {
        "total_cases": len(cases),
        "evaluated_cases": total,
        "skipped_cases": len(results) - total,
        "top_k": top_k,
        "document_type_hit_rate": round(type_hits / total, 4) if total else 0.0,
        "average_keyword_hit_rate": round(sum(keyword_rates) / total, 4) if total else 0.0,
        "average_retrieval_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "results": results,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

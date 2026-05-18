"""Measure assistant and RAG latency for common local queries."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.answer_service import (  # noqa: E402
    build_prompt,
    deterministic_curriculum_answer,
    deterministic_leadership_answer,
    deterministic_programming_answer,
    filter_retrieval_results,
    retrieval_confidence,
)
from backend.app.services.citation_service import build_citations  # noqa: E402
from backend.app.services.llm_service import OllamaService  # noqa: E402
from backend.app.services.retriever_service import get_retriever_service  # noqa: E402
from orchestration.intent_classifier_v2 import classify_intent_v2  # noqa: E402


QUERIES = [
    "khoa học dữ liệu học những môn gì",
    "hiệu trưởng HUS là ai",
    "hôm nay tôi cần làm gì",
    "giải thích AI là gì",
    "ngành này có học lập trình không?",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark local assistant latency.")
    parser.add_argument("--output", default="qa_ba/reports/latency_benchmark_before.json")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--session-prefix", default="benchmark")
    return parser.parse_args()


def timed(fn):
    started = time.perf_counter()
    value = fn()
    return value, int((time.perf_counter() - started) * 1000)


def post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(f"{base_url}{path}", data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    with request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def measure_direct_rag(query: str) -> dict[str, Any]:
    classifier = classify_intent_v2(query)
    if classifier.intent not in {"institutional_rag", "rag"}:
        return {"mode": classifier.intent, "skipped": True}

    retriever_service = get_retriever_service()
    timings: dict[str, int] = {}

    _, timings["embedding_latency_ms"] = timed(lambda: retriever_service.embedding_model.embed_query(query))
    raw_results, timings["qdrant_retrieval_plus_rerank_latency_ms"] = timed(
        lambda: retriever_service.retrieve(query, top_k=6)
    )
    results, timings["answer_synthesis_latency_ms"] = timed(
        lambda: filter_retrieval_results(raw_results, query=query)
    )
    llm = OllamaService()
    llm_available = llm.is_available()
    generated = None
    deterministic = (
        deterministic_leadership_answer(query, results)
        or deterministic_programming_answer(query, results)
        or deterministic_curriculum_answer(query, results)
    )
    if deterministic:
        timings["llm_generation_latency_ms"] = 0
        generated = deterministic.answer
    elif llm_available and results:
        prompt = build_prompt(query, results[:4], None)
        generated, timings["llm_generation_latency_ms"] = timed(
            lambda: llm.generate(prompt, temperature=0.0, num_ctx=3072)
        )
    else:
        timings["llm_generation_latency_ms"] = 0

    _, timings["citation_formatting_latency_ms"] = timed(
        lambda: build_citations(results, answer=generated or "", query=query, cited_only=True)
    )
    return {
        "mode": classifier.intent,
        "skipped": False,
        "llm_available": llm_available,
        "retrieval_confidence": retrieval_confidence(results),
        "source_count": len(results),
        "deterministic_fast_path": bool(deterministic),
        **timings,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    report_path = PROJECT_ROOT / args.output
    report_path.parent.mkdir(parents=True, exist_ok=True)

    health, health_ms = timed(lambda: json.loads(request.urlopen(f"{args.base_url}/health", timeout=10).read()))
    # Warm the local benchmark process so per-query embedding timings do not include model load.
    try:
        _ = get_retriever_service().embedding_model.info
    except Exception:
        pass
    cases = []
    for index, query in enumerate(QUERIES, start=1):
        assistant_payload = {
            "user_id": "benchmark",
            "session_id": f"{args.session_prefix}-{index}",
            "message": query,
            "include_memory": False,
            "use_mock_google": True,
        }
        assistant_response, total_ms = timed(
            lambda payload=assistant_payload: post_json(args.base_url, "/api/assistant/chat", payload)
        )
        direct = measure_direct_rag(query)
        cases.append(
            {
                "query": query,
                "total_latency_ms": total_ms,
                "first_token_latency_ms": None,
                "assistant_intent": assistant_response.get("intent"),
                "assistant_mode": (assistant_response.get("metadata") or {}).get("rag", {}).get("mode")
                or (assistant_response.get("metadata") or {}).get("general_llm_mode")
                or assistant_response.get("intent"),
                "assistant_source_count": len(assistant_response.get("sources") or []),
                "assistant_metadata_latency_ms": (assistant_response.get("metadata") or {}).get("latency_ms"),
                "direct_rag": direct,
            }
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": health,
        "health_latency_ms": health_ms,
        "cases": cases,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"latency_benchmark_report={report_path}")
    for item in cases:
        direct = item["direct_rag"]
        print(
            f"{item['total_latency_ms']:>5} ms | {item['assistant_intent']:<18} | "
            f"{item['assistant_mode']} | {item['query']}"
        )
        if not direct.get("skipped"):
            print(
                "      "
                f"embed={direct.get('embedding_latency_ms')} "
                f"retrieval+rerrank={direct.get('qdrant_retrieval_plus_rerank_latency_ms')} "
                f"llm={direct.get('llm_generation_latency_ms')} "
                f"cite={direct.get('citation_formatting_latency_ms')}"
            )


if __name__ == "__main__":
    main()

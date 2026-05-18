"""Evaluate assistant behavior against promoted feedback cases."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from orchestration.assistant_graph import AssistantGraph


def evaluate_feedback_cases(eval_path: Path, *, backend_url: str | None = None) -> dict[str, Any]:
    cases = read_jsonl(eval_path)
    assistant = None if backend_url and backend_available(backend_url) else AssistantGraph()
    results: list[dict[str, Any]] = []
    pass_count = 0
    evaluated_count = 0
    skipped_count = 0
    latencies: list[int] = []

    for index, case in enumerate(cases, start=1):
        query = str(case.get("query") or "")
        if should_skip_case(case):
            skipped_count += 1
            results.append(
                {
                    "query": query,
                    "reason": case.get("reason"),
                    "expected_behavior": case.get("expected_behavior"),
                    "passed": None,
                    "skipped": True,
                    "skip_reason": "synthetic_placeholder_query",
                    "checks": {},
                    "intent": None,
                    "sources_count": 0,
                    "quality": {},
                    "latency_ms": 0,
                    "answer_preview": "",
                }
            )
            continue
        started = time.perf_counter()
        state = invoke_assistant(
            query=query,
            index=index,
            backend_url=backend_url,
            assistant=assistant,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        latencies.append(latency_ms)
        checks = evaluate_case(case, state)
        passed = all(checks.values())
        evaluated_count += 1
        pass_count += int(passed)
        results.append(
            {
                "query": query,
                "reason": case.get("reason"),
                "expected_behavior": case.get("expected_behavior"),
                "passed": passed,
                "checks": checks,
                "intent": state.get("intent"),
                "sources_count": len(state.get("sources", [])),
                "quality": state.get("metadata", {}).get("quality", {}),
                "latency_ms": latency_ms,
                "answer_preview": str(state.get("answer") or "")[:500],
            }
        )

    total = len(results)
    return {
        "total_cases": total,
        "evaluated_cases": evaluated_count,
        "skipped_cases": skipped_count,
        "passed_cases": pass_count,
        "pass_rate": round(pass_count / evaluated_count, 4) if evaluated_count else 0.0,
        "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "results": results,
    }


def should_skip_case(case: dict[str, Any]) -> bool:
    query = str(case.get("query") or "").strip().lower()
    if query.startswith("feedback eval "):
        return True
    if query in {"helpful answer", "test", "smoke"}:
        return True
    if "?" in query and any(marker in query for marker in ("hi?u", "tr??ng", "gi?m")):
        return True
    return False


def backend_available(backend_url: str) -> bool:
    try:
        response = httpx.get(f"{backend_url.rstrip('/')}/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def invoke_assistant(
    *,
    query: str,
    index: int,
    backend_url: str | None,
    assistant: AssistantGraph | None,
) -> dict[str, Any]:
    if backend_url:
        try:
            response = httpx.post(
                f"{backend_url.rstrip('/')}/api/assistant/chat",
                json={
                    "user_id": "feedback-eval",
                    "session_id": f"feedback-eval-{index}",
                    "message": query,
                    "include_memory": True,
                    "use_mock_google": True,
                },
                timeout=90.0,
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "answer": data.get("answer", ""),
                    "intent": data.get("intent", ""),
                    "sources": data.get("sources", []),
                    "metadata": data.get("metadata", {}),
                }
        except Exception:
            pass
    fallback = assistant or AssistantGraph()
    return fallback.invoke(
        user_id="feedback-eval",
        session_id=f"feedback-eval-{index}",
        message=query,
        include_memory=True,
        use_mock_google=True,
    )


def evaluate_case(case: dict[str, Any], state: dict[str, Any]) -> dict[str, bool]:
    answer = str(state.get("answer") or "")
    sources = state.get("sources", [])
    quality = state.get("metadata", {}).get("quality", {})
    correction = str(case.get("correction") or "")
    reason = str(case.get("reason") or "")
    checks = {
        "answer_not_empty": bool(answer.strip()),
        "quality_score_threshold": float(quality.get("quality_score", 0.0)) >= 0.45,
    }
    if correction:
        checks["correction_partial_alignment"] = token_overlap(answer, correction) >= 0.2
    if reason == "missing_source":
        checks["sources_exist"] = bool(sources)
    if reason == "irrelevant_retrieval":
        source_ids = [
            str(source.get("source_url") or source.get("chunk_id") or source.get("type"))
            for source in sources
            if isinstance(source, dict)
        ]
        checks["sources_not_all_same"] = len(set(source_ids)) > 1 if source_ids else False
    return checks


def token_overlap(answer: str, correction: str) -> float:
    answer_tokens = meaningful_tokens(answer)
    correction_tokens = meaningful_tokens(correction)
    if not correction_tokens:
        return 1.0
    return len(answer_tokens.intersection(correction_tokens)) / len(correction_tokens)


def meaningful_tokens(value: str) -> set[str]:
    return {token.strip(".,;:!?()[]{}").lower() for token in value.split() if len(token.strip(".,;:!?()[]{}")) >= 4}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

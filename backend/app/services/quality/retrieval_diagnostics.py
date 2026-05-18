"""Diagnostics for retrieval source quality."""

from __future__ import annotations

from collections import Counter
from typing import Any


LOW_SCORE_THRESHOLD = 0.45


def retrieval_scores(sources: list[dict[str, Any]]) -> list[float]:
    scores: list[float] = []
    for source in sources:
        score = source.get("score")
        if isinstance(score, (int, float)):
            scores.append(float(score))
    return scores


def repeated_source_issues(sources: list[dict[str, Any]], *, max_repeat: int = 3) -> list[str]:
    identifiers = [
        str(source.get("source_url") or source.get("message_id") or source.get("event_id") or source.get("type"))
        for source in sources
        if source.get("source_url") or source.get("message_id") or source.get("event_id") or source.get("type")
    ]
    counter = Counter(identifiers)
    return [f"source_repeated:{source}" for source, count in counter.items() if count > max_repeat]


def has_very_low_scores(sources: list[dict[str, Any]]) -> bool:
    scores = retrieval_scores(sources)
    return bool(scores) and max(scores) < LOW_SCORE_THRESHOLD

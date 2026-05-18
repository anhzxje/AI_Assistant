"""Compatibility wrapper for deterministic assistant routing."""

from __future__ import annotations

from typing import Any

from orchestration.assistant_brain import build_plan, looks_institutional_query, normalize_text


Intent = str


def classify_intent(message: str, *, recent_turns: list[dict[str, Any]] | None = None) -> Intent:
    return build_plan(message, recent_turns=recent_turns).intent

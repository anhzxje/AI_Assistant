"""Feature loading utilities for training and evaluation jobs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_platform.config import get_settings


def latest_chunks_path() -> Path:
    root = get_settings().resolved_data_root / "features" / "chunks"
    candidates = sorted(root.glob("*/document_chunks.jsonl"))
    if not candidates:
        raise FileNotFoundError(f"No feature chunks found under {root}")
    return candidates[-1]


def load_chunks(limit: int | None = None) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in latest_chunks_path().read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[:limit] if limit else rows


def load_eval_cases(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or Path("qa_ba/test_cases/rag_eval_questions.jsonl")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

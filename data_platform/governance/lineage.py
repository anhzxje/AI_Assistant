"""Append-only lineage records for data and model operations."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from data_platform.config import get_settings


def lineage_path() -> Path:
    return get_settings().metadata_root / "lineage.jsonl"


def append_lineage(event_type: str, *, inputs: list[str], outputs: list[str], metadata: dict[str, Any] | None = None) -> Path:
    path = lineage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event_type": event_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": inputs,
        "outputs": outputs,
        "metadata": metadata or {},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def lineage_status(limit: int = 10) -> dict[str, Any]:
    path = lineage_path()
    if not path.exists():
        append_lineage("metadata_initialized", inputs=[], outputs=["data/metadata"], metadata={"mode": "mvp"})
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "path": str(path),
        "event_count": len(rows),
        "recent_events": rows[-limit:],
        "status": "available",
    }

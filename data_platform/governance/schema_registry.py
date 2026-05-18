"""Lightweight schema registry for data lake artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from data_platform.config import get_settings


DEFAULT_SCHEMAS: dict[str, dict[str, Any]] = {
    "processed_document": {
        "required": ["document_id", "source_url", "source_path", "title", "text", "document_type", "content_hash"],
        "optional": ["published_date", "language", "headings", "links", "tables", "metadata"],
    },
    "feature_chunk": {
        "required": ["chunk_id", "document_id", "source_url", "text", "character_start", "character_end", "features"],
        "optional": ["preview_text", "section_heading", "context_before", "context_after", "metadata"],
    },
    "feedback_record": {
        "required": ["feedback_id", "query", "answer", "rating", "reason", "status", "created_at"],
        "optional": ["correction", "diagnostics", "sources", "admin_note"],
    },
}


def registry_path() -> Path:
    return get_settings().metadata_root / "schema_registry.json"


def ensure_schema_registry() -> dict[str, Any]:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    registry = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schemas": DEFAULT_SCHEMAS,
    }
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return registry


def schema_registry_status() -> dict[str, Any]:
    registry = ensure_schema_registry()
    return {
        "path": str(registry_path()),
        "version": registry.get("version"),
        "schema_count": len(registry.get("schemas") or {}),
        "schemas": sorted((registry.get("schemas") or {}).keys()),
        "status": "available",
    }

"""Validate chunk feature JSONL files."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from qa_ba.data_quality.validate_processed_docs import VALID_DOCUMENT_TYPES

REQUIRED_FIELDS = {
    "chunk_id",
    "document_id",
    "source_url",
    "source_path",
    "title",
    "document_type",
    "chunk_index",
    "text",
    "character_start",
    "character_end",
    "content_hash",
    "features",
    "metadata",
}


def validate_chunks(path: Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    chunk_ids = Counter(str(row.get("chunk_id")) for row in rows)
    issues: list[dict[str, Any]] = []
    lengths: list[int] = []
    missing_preview_count = 0
    language_anomaly_count = 0

    for line_number, row in enumerate(rows, start=1):
        missing = sorted(field for field in REQUIRED_FIELDS if field not in row)
        if missing:
            issues.append({"line": line_number, "type": "missing_fields", "fields": missing})
            continue

        features = row.get("features") or {}
        text = str(row.get("text") or "")
        lengths.append(len(text))
        if not text.strip():
            issues.append({"line": line_number, "type": "empty_text"})
        if len(text) < 80:
            issues.append({"line": line_number, "type": "chunk_too_short", "length": len(text)})
        if len(text) > 2200:
            issues.append({"line": line_number, "type": "chunk_too_long", "length": len(text)})
        if int(row.get("character_start", -1)) < 0 or int(row.get("character_end", -1)) <= int(row.get("character_start", -1)):
            issues.append({"line": line_number, "type": "invalid_offsets"})
        if not row.get("source_url") or not row.get("source_path") or row.get("chunk_index") is None:
            issues.append({"line": line_number, "type": "missing_citation_metadata"})
        if not (row.get("preview_text") or features.get("preview_text")):
            missing_preview_count += 1
            issues.append({"line": line_number, "type": "missing_preview_text"})
        if row.get("document_type") not in VALID_DOCUMENT_TYPES:
            issues.append({"line": line_number, "type": "invalid_document_type", "value": row.get("document_type")})
        for score_name in ("authority_score", "freshness_score", "content_quality_score", "boilerplate_score"):
            score = features.get(score_name)
            if not isinstance(score, (int, float)) or not 0.0 <= float(score) <= 1.0:
                issues.append({"line": line_number, "type": f"invalid_{score_name}", "value": score})
        if features.get("boilerplate_score", 0) and float(features.get("boilerplate_score") or 0) > 0.65:
            issues.append({"line": line_number, "type": "high_boilerplate_score", "value": features.get("boilerplate_score")})
        if looks_like_language_anomaly(text):
            language_anomaly_count += 1
            issues.append({"line": line_number, "type": "language_anomaly"})

    duplicate_chunk_id_count = sum(count - 1 for count in chunk_ids.values() if count > 1)
    if duplicate_chunk_id_count:
        issues.append({"type": "duplicate_chunk_ids", "count": duplicate_chunk_id_count})

    return {
        "path": str(path),
        "total_chunks": len(rows),
        "issue_count": len(issues),
        "issues": issues[:100],
        "duplicate_chunk_id_count": duplicate_chunk_id_count,
        "chunks_by_document_type": dict(Counter(str(row.get("document_type")) for row in rows)),
        "missing_preview_count": missing_preview_count,
        "language_anomaly_count": language_anomaly_count,
        "chunk_length": {
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "average": round(sum(lengths) / len(lengths), 2) if lengths else 0,
            "outlier_count": sum(1 for value in lengths if value < 80 or value > 2200),
        },
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def looks_like_language_anomaly(text: str) -> bool:
    lowered = text.lower()
    foreign_markers = [" terming ", " kehidup", " dari ", " adalah ", " dimana "]
    return any(marker in lowered for marker in foreign_markers)

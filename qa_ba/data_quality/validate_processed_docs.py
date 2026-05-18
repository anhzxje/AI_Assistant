"""Validate processed document JSONL files."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

VALID_DOCUMENT_TYPES = {
    "announcement",
    "curriculum",
    "lecturer_profile",
    "admission",
    "regulation",
    "program",
    "leadership",
    "department",
    "quality_assurance",
    "general_info",
    "organization",
    "contact",
    "error_page",
    "unknown",
}

REQUIRED_FIELDS = {
    "document_id",
    "source_url",
    "source_path",
    "source_type",
    "title",
    "text",
    "language",
    "document_type",
    "processed_time",
    "content_hash",
    "raw_content_hash",
}


def validate_processed_documents(path: Path, *, min_text_length: int = 120) -> dict[str, Any]:
    rows = read_jsonl(path)
    content_hashes = Counter(str(row.get("content_hash")) for row in rows)
    issues: list[dict[str, Any]] = []
    missing_title_count = 0
    stale_or_unknown_date_count = 0
    language_missing_count = 0
    empty_docs_count = 0
    too_long_docs_count = 0
    high_boilerplate_count = 0
    language_anomaly_count = 0

    for line_number, row in enumerate(rows, start=1):
        missing = sorted(field for field in REQUIRED_FIELDS if field not in row)
        if missing:
            issues.append({"line": line_number, "type": "missing_fields", "fields": missing})

        text = str(row.get("text") or "")
        text_length = len(text)
        if not text.strip():
            empty_docs_count += 1
            issues.append({"line": line_number, "type": "empty_document"})
        if text_length < min_text_length:
            issues.append({"line": line_number, "type": "text_too_short"})
        if text_length > 50000:
            too_long_docs_count += 1
            issues.append({"line": line_number, "type": "text_too_long", "length": text_length})
        if not row.get("source_url") or not row.get("source_path"):
            issues.append({"line": line_number, "type": "missing_source"})
        if row.get("document_type") not in VALID_DOCUMENT_TYPES:
            issues.append({"line": line_number, "type": "invalid_document_type", "value": row.get("document_type")})
        if not row.get("title"):
            missing_title_count += 1
        if not row.get("language") or row.get("language") == "unknown":
            language_missing_count += 1
        if not row.get("published_date"):
            stale_or_unknown_date_count += 1
        density = menu_or_boilerplate_density(text)
        if density > 0.35:
            high_boilerplate_count += 1
            issues.append({"line": line_number, "type": "high_boilerplate_density", "density": round(density, 3)})
        if row.get("language") == "vi" and looks_like_language_anomaly(text):
            language_anomaly_count += 1
            issues.append({"line": line_number, "type": "language_anomaly"})

    duplicate_hash_count = sum(count - 1 for count in content_hashes.values() if count > 1)
    return {
        "path": str(path),
        "total_documents": len(rows),
        "issue_count": len(issues),
        "issues": issues[:100],
        "duplicate_content_hash_count": duplicate_hash_count,
        "missing_title_count": missing_title_count,
        "language_missing_or_unknown_count": language_missing_count,
        "stale_or_unknown_date_count": stale_or_unknown_date_count,
        "empty_docs_count": empty_docs_count,
        "too_long_docs_count": too_long_docs_count,
        "high_boilerplate_count": high_boilerplate_count,
        "language_anomaly_count": language_anomaly_count,
        "valid_document_types": dict(Counter(str(row.get("document_type")) for row in rows)),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def menu_or_boilerplate_density(text: str) -> float:
    if not text:
        return 0.0
    markers = ["menu", "đăng nhập", "search", "trang chủ", "liên hệ", "copyright", "facebook"]
    lowered = text.lower()
    return sum(lowered.count(marker) for marker in markers) / max(len(text.split()), 1)


def looks_like_language_anomaly(text: str) -> bool:
    lowered = text.lower()
    foreign_markers = [" terming ", " kehidup", " dari ", " adalah ", " dimana "]
    return any(marker in lowered for marker in foreign_markers)

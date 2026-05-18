"""Data quality checks for CSV/JSON/Excel file ingestion evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_TYPES = {"csv", "json", "excel"}
REQUIRED_COLUMNS = {
    "students_sample": {"student_id", "full_name", "program", "cohort", "email", "status"},
    "courses_sample": {"course_code", "course_name", "credits", "department", "program", "semester"},
    "schedule_sample": {"sheet_name"},
}


def validate_file_ingestion(data_root: Path) -> dict[str, Any]:
    manifest_path = data_root / "metadata" / "file_ingestion_manifest.jsonl"
    records = read_jsonl(manifest_path)
    latest_success = latest_success_records(records)
    issues: list[dict[str, Any]] = []

    if not records:
        issues.append(issue("missing_manifest", "data/metadata/file_ingestion_manifest.jsonl was not found or is empty."))

    failed = [record for record in records if record.get("status") == "failed"]
    for record in failed:
        issues.append(issue("failed_ingestion", f"{record.get('source_path')} failed: {record.get('errors')}"))

    present_types = {record.get("file_type") for record in latest_success}
    for file_type in REQUIRED_TYPES - present_types:
        issues.append(issue("missing_file_type", f"No successful {file_type} ingestion found."))

    for record in latest_success:
        stem = Path(str(record.get("source_path") or "")).stem
        columns = set(record.get("columns") or [])
        required = REQUIRED_COLUMNS.get(stem, set())
        missing = sorted(required - columns)
        if missing:
            issues.append(issue("missing_required_columns", f"{stem} missing columns: {missing}"))
        if int(record.get("row_count") or 0) <= 0 and stem != "empty":
            issues.append(issue("empty_processed_file", f"{stem} has no processed rows."))
        processed_path = Path(str(record.get("processed_path") or ""))
        if processed_path and not processed_path.exists():
            issues.append(issue("missing_processed_output", f"{processed_path} does not exist."))

    type_summary = {}
    for file_type in REQUIRED_TYPES:
        matching = [record for record in latest_success if record.get("file_type") == file_type]
        type_summary[file_type] = {
            "count": len(matching),
            "rows": sum(int(record.get("row_count") or 0) for record in matching),
            "status": "ok" if matching else "missing",
        }

    return {
        "manifest_path": str(manifest_path),
        "record_count": len(records),
        "latest_success_count": len(latest_success),
        "required_types": sorted(REQUIRED_TYPES),
        "type_summary": type_summary,
        "issue_count": len(issues),
        "issues": issues,
    }


def latest_success_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_source: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.get("status") != "success":
            continue
        source = str(record.get("source_path") or "")
        previous = by_source.get(source)
        if previous is None or str(record.get("ingested_at") or "") >= str(previous.get("ingested_at") or ""):
            by_source[source] = record
    return list(by_source.values())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def issue(name: str, detail: str) -> dict[str, str]:
    return {"name": name, "detail": detail}

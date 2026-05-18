"""Ingest CSV/JSON/Excel files into raw, processed, metadata, and feature layers."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_platform.config import get_settings
from data_platform.ingestion.parsers.tabular_parser import SUPPORTED_EXTENSIONS, parse_tabular_file


FILE_TYPES = {".csv": "csv", ".json": "json", ".jsonl": "json", ".xlsx": "excel"}
DATE_COLUMN_HINTS = ("date", "exam_date")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest local CSV/JSON/Excel files.")
    parser.add_argument("--input", required=True, help="Input file or directory.")
    parser.add_argument("--latest", action="store_true", help="Use today's partition.")
    args = parser.parse_args()

    input_path = (PROJECT_ROOT / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input)
    partition = date.today().isoformat() if args.latest else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    settings = get_settings()
    data_root = settings.resolved_data_root
    raw_root = data_root / "raw" / "files" / partition
    processed_root = data_root / "processed" / "files" / partition
    features_root = data_root / "features" / "tabular" / partition
    manifest_path = data_root / "metadata" / "file_ingestion_manifest.jsonl"

    files = discover_files(input_path)
    manifest_records: list[dict[str, Any]] = []
    processed_records_by_file: list[tuple[Path, list[dict[str, Any]], str]] = []

    for source in files:
        record = base_manifest_record(source)
        try:
            raw_path = raw_root / source.name
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, raw_path)

            rows = [normalize_row(row) for row in parse_tabular_file(source)]
            processed_path = processed_root / f"{source.stem}.jsonl"
            write_jsonl(processed_path, rows)
            processed_records_by_file.append((processed_path, rows, FILE_TYPES[source.suffix.lower()]))

            record.update(
                {
                    "raw_path": str(raw_path),
                    "processed_path": str(processed_path),
                    "file_type": FILE_TYPES[source.suffix.lower()],
                    "row_count": len(rows),
                    "column_count": len(sorted({key for row in rows for key in row})),
                    "columns": sorted({key for row in rows for key in row}),
                    "content_hash": sha256_file(source),
                    "status": "success",
                }
            )
        except Exception as exc:  # noqa: BLE001 - manifest should preserve file-level failures.
            record.update({"status": "failed", "errors": [str(exc)]})
        manifest_records.append(record)

    append_jsonl(manifest_path, manifest_records)
    summary = build_feature_summary(processed_records_by_file, manifest_records)
    features_root.mkdir(parents=True, exist_ok=True)
    summary_path = features_root / "tabular_feature_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"manifest={manifest_path}")
    print(f"feature_summary={summary_path}")
    print(f"files={len(files)} success={sum(1 for item in manifest_records if item['status'] == 'success')}")


def discover_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        candidates = [input_path]
    else:
        candidates = sorted(path for path in input_path.iterdir() if path.is_file())
    return [path for path in candidates if path.suffix.lower() in SUPPORTED_EXTENSIONS]


def base_manifest_record(source: Path) -> dict[str, Any]:
    return {
        "source_path": str(source),
        "raw_path": "",
        "processed_path": "",
        "file_type": FILE_TYPES.get(source.suffix.lower(), "unknown"),
        "row_count": 0,
        "column_count": 0,
        "columns": [],
        "content_hash": sha256_file(source) if source.exists() else "",
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "errors": [],
    }


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        column = snake_case(str(key))
        normalized[column] = normalize_value(column, value)
    return normalized


def normalize_value(column: str, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        text = " ".join(value.strip().split())
        if text == "":
            return None
        if any(hint in column for hint in DATE_COLUMN_HINTS):
            parsed = parse_date(text)
            return parsed or text
        return text
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def parse_date(value: str) -> str | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def snake_case(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_feature_summary(
    processed_records_by_file: list[tuple[Path, list[dict[str, Any]], str]],
    manifest_records: list[dict[str, Any]],
) -> dict[str, Any]:
    row_counts = {path.name: len(rows) for path, rows, _ in processed_records_by_file}
    missing_counts: dict[str, int] = defaultdict(int)
    unique_programs: set[str] = set()
    unique_courses: set[str] = set()
    exam_dates: set[str] = set()
    class_schedule_counts: Counter[str] = Counter()
    searchable_text: list[dict[str, Any]] = []

    for path, rows, file_type in processed_records_by_file:
        for row in rows:
            for key, value in row.items():
                if value is None:
                    missing_counts[key] += 1
            if row.get("program"):
                unique_programs.add(str(row["program"]))
            if row.get("course_name"):
                unique_courses.add(str(row["course_name"]))
            if row.get("exam_date"):
                exam_dates.add(str(row["exam_date"]))
            if row.get("sheet_name") == "classes" or row.get("class_id"):
                class_schedule_counts[str(row.get("weekday") or "unknown")] += 1
            searchable_text.append(
                {
                    "source_file": path.name,
                    "document_type": infer_document_type(row, file_type),
                    "source_scope": "sample_demo",
                    "text": " | ".join(f"{key}: {value}" for key, value in row.items() if value is not None),
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_scope": "sample_demo",
        "manifest_records": len(manifest_records),
        "row_counts": row_counts,
        "missing_value_counts": dict(sorted(missing_counts.items())),
        "unique_programs": sorted(unique_programs),
        "unique_courses": sorted(unique_courses),
        "exam_dates": sorted(exam_dates),
        "class_schedule_counts": dict(class_schedule_counts),
        "searchable_text_summaries": searchable_text,
    }


def infer_document_type(row: dict[str, Any], file_type: str) -> str:
    if row.get("student_id"):
        return "student_record_mock"
    if row.get("course_code"):
        return "course_catalog"
    if row.get("exam_id"):
        return "exam_schedule"
    if row.get("class_id"):
        return "class_schedule"
    return f"{file_type}_sample"


if __name__ == "__main__":
    main()

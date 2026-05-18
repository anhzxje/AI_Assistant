"""Tests for CSV/JSON/Excel sample file ingestion evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from qa_ba.api_tests.auth_helpers import admin_headers


SAMPLES = Path("data/samples/files")
MANIFEST = Path("data/metadata/file_ingestion_manifest.jsonl")


def test_sample_files_exist() -> None:
    assert (SAMPLES / "students_sample.csv").exists()
    assert (SAMPLES / "courses_sample.json").exists()
    assert (SAMPLES / "schedule_sample.xlsx").exists()


def test_run_ingest_files_parses_csv_json_excel() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_ingest_files.py", "--input", "data/samples/files", "--latest"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "success=3" in result.stdout
    records = read_jsonl(MANIFEST)
    latest = latest_success_by_source(records)
    file_types = {record["file_type"] for record in latest}
    assert {"csv", "json", "excel"}.issubset(file_types)
    assert all(int(record["row_count"]) > 0 for record in latest if record["file_type"] in {"csv", "json", "excel"})


def test_data_quality_report_includes_file_ingestion() -> None:
    subprocess.run([sys.executable, "scripts/run_data_quality.py"], check=True, capture_output=True, text=True)
    report = json.loads(Path("qa_ba/reports/data_quality_report.json").read_text(encoding="utf-8"))

    assert "file_ingestion" in report
    assert report["file_ingestion"]["issue_count"] == 0
    assert report["file_ingestion"]["type_summary"]["csv"]["status"] == "ok"
    assert report["file_ingestion"]["type_summary"]["json"]["status"] == "ok"
    assert report["file_ingestion"]["type_summary"]["excel"]["status"] == "ok"


def test_admin_data_layer_summary_includes_file_ingestion() -> None:
    client = TestClient(app)
    response = client.get("/api/admin/data-layer-summary", headers=admin_headers(client))

    assert response.status_code == 200
    body = response.json()
    assert body["file_ingestion"]["csv"]["status"] == "ok"
    assert body["file_ingestion"]["json"]["status"] == "ok"
    assert body["file_ingestion"]["excel"]["status"] == "ok"
    assert body["file_ingestion"]["csv"]["rows"] > 0
    assert body["file_ingestion"]["json"]["rows"] > 0
    assert body["file_ingestion"]["excel"]["rows"] > 0


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def latest_success_by_source(records: list[dict]) -> list[dict]:
    by_source: dict[str, dict] = {}
    for record in records:
        if record.get("status") != "success":
            continue
        source = str(record.get("source_path") or "")
        previous = by_source.get(source)
        if previous is None or str(record.get("ingested_at") or "") >= str(previous.get("ingested_at") or ""):
            by_source[source] = record
    return list(by_source.values())

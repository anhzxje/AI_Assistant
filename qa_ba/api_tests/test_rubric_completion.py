"""Rubric completion smoke tests for data layer and AI serving."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from data_platform.ingestion.parsers.tabular_parser import parse_tabular_file
from qa_ba.api_tests.auth_helpers import admin_headers


def test_admin_data_layer_summary() -> None:
    client = TestClient(app)
    response = client.get("/api/admin/data-layer-summary", headers=admin_headers(client))

    assert response.status_code == 200
    body = response.json()
    assert "raw" in body["layers"]
    assert "processed" in body["layers"]
    assert "features" in body["layers"]
    assert body["schema_registry"]["status"] == "available"
    assert body["governance"]["raw_immutable"] is True
    assert "allowed_domains" in body["governance"]


def test_predict_endpoint_routes_to_assistant() -> None:
    response = TestClient(app).post(
        "/api/predict",
        json={"query": "hôm nay là ngày nào", "include_memory": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["prediction"]
    assert body["intent"] == "date_time"
    assert body["confidence"] >= 0


def test_tabular_parser_csv_sample() -> None:
    rows = parse_tabular_file(Path("data/raw/files/sample/student_services_sample.csv"))

    assert rows
    assert rows[0]["document_type"] == "student_procedure"

"""Tests for admin BI read endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from qa_ba.api_tests.auth_helpers import admin_headers


def test_admin_system_summary() -> None:
    client = TestClient(app)
    headers = admin_headers(client)

    response = client.get("/api/admin/system-summary", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["health"]["status"] == "ok"
    assert "qdrant_points" in body["health"]
    assert body["data"]["total_documents"] >= 0
    assert body["data"]["total_chunks"] >= 0
    assert isinstance(body["data"]["chunks_by_document_type"], dict)
    assert isinstance(body["data"]["source_health"], list)
    assert isinstance(body["data"]["missing_knowledge_indicators"], list)
    assert "data_quality" in body["qa"]
    assert "retrieval_eval" in body["qa"]
    assert "rag_eval" in body["qa"]
    assert "feedback_eval" in body["qa"]
    assert "total" in body["feedback"]
    assert "pending" in body["jobs"]


def test_admin_chunks_endpoint() -> None:
    client = TestClient(app)
    headers = admin_headers(client)

    response = client.get("/api/admin/chunks?limit=3", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= body["count"]
    assert body["count"] <= 3
    if body["chunks"]:
        chunk = body["chunks"][0]
        assert "chunk_id" in chunk
        assert "document_id" in chunk
        assert "preview" in chunk


def test_admin_document_detail_endpoint() -> None:
    client = TestClient(app)
    headers = admin_headers(client)
    listed = client.get("/api/admin/documents?limit=1", headers=headers)
    assert listed.status_code == 200
    documents = listed.json()["documents"]
    assert documents
    document_id = documents[0]["document_id"]

    detail = client.get(f"/api/admin/document/{document_id}", headers=headers)

    assert detail.status_code == 200
    body = detail.json()
    assert body["document"]["document_id"] == document_id
    assert "chunks" in body
    assert body["chunk_count"] == len(body["chunks"])

"""Tests for feedback APIs."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from data_platform.feedback.feedback_store import FeedbackStore
from data_platform.jobs.job_store import JobStore
from qa_ba.api_tests.auth_helpers import admin_headers


def test_feedback_create_and_admin_list() -> None:
    client = TestClient(app)
    headers = admin_headers(client)
    marker = f"feedback query {uuid.uuid4()}"

    created = client.post(
        "/api/feedback",
        json={
            "user_id": "feedback-test",
            "session_id": "feedback-session",
            "message_id": str(uuid.uuid4()),
            "rating": "down",
            "reason": "wrong_answer",
            "correction": "Use the cited source.",
            "query": marker,
            "answer": "Old answer",
            "intent": "institutional_rag",
            "route": ["conversation_context", "intent_classifier_v2", "rag_node"],
            "sources": [{"source_url": "https://example.edu"}],
        },
    )

    assert created.status_code == 200
    created_body = created.json()
    feedback_id = created_body["feedback_id"]
    assert created_body["severity"] == "high"
    assert created_body["diagnostics"]["source_count"] == 1

    listed = client.get(
        "/api/admin/feedback?rating=down&reason=wrong_answer&status=new&severity=high&intent=institutional_rag",
        headers=headers,
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["count"] >= 1
    assert any(item["feedback_id"] == feedback_id and item["query"] == marker for item in body["feedback"])


def test_feedback_admin_update() -> None:
    client = TestClient(app)
    headers = admin_headers(client)
    created = client.post(
        "/api/feedback",
        json={
            "rating": "up",
            "reason": "other",
            "query": "test",
            "answer": "ok",
            "sources": [],
        },
    )
    assert created.status_code == 200
    feedback_id = created.json()["feedback_id"]

    updated = client.patch(
        f"/api/admin/feedback/{feedback_id}",
        json={"status": "reviewed", "admin_note": "Checked in API test."},
        headers=headers,
    )

    assert updated.status_code == 200
    assert updated.json()["status"] == "reviewed"
    assert updated.json()["admin_note"] == "Checked in API test."


def test_feedback_upvote_defaults_reason() -> None:
    client = TestClient(app)
    created = client.post(
        "/api/feedback",
        json={
            "rating": "up",
            "query": "helpful answer",
            "answer": "ok",
            "sources": [],
        },
    )

    assert created.status_code == 200
    assert created.json()["reason"] == "other"


def test_feedback_downvote_requires_reason() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/feedback",
        json={
            "rating": "down",
            "query": "bad answer",
            "answer": "bad",
            "sources": [],
        },
    )

    assert response.status_code == 422


def test_feedback_summary_promote_and_queues(monkeypatch, tmp_path: Path) -> None:
    install_temp_stores(monkeypatch, tmp_path)
    client = TestClient(app)
    headers = admin_headers(client)
    created = client.post(
        "/api/feedback",
        json={
            "rating": "down",
            "reason": "missing_source",
            "query": f"feedback eval {uuid.uuid4()}",
            "answer": "No source",
            "intent": "institutional_rag",
            "route": ["rag_node"],
            "sources": [],
            "correction": "Should cite an admissions source.",
        },
    )
    assert created.status_code == 200
    feedback_id = created.json()["feedback_id"]

    summary = client.get("/api/admin/feedback/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total"] >= 1
    assert summary.json()["recommended_actions"]

    promoted = client.post(f"/api/admin/feedback/{feedback_id}/promote-to-eval", headers=headers)
    assert promoted.status_code == 200
    assert promoted.json()["promoted"] is True

    reindex = client.post(f"/api/admin/feedback/{feedback_id}/queue-reindex", headers=headers)
    assert reindex.status_code == 200
    assert reindex.json()["queued"] is True
    assert reindex.json()["status"] == "queued_for_reindex"

    recrawl = client.post(f"/api/admin/feedback/{feedback_id}/queue-recrawl", headers=headers)
    assert recrawl.status_code == 200
    assert recrawl.json()["queued"] is True
    assert recrawl.json()["status"] == "queued_for_recrawl"


def install_temp_stores(monkeypatch, tmp_path: Path) -> None:
    from backend.app.api import feedback as feedback_api
    from backend.app.api import jobs as jobs_api

    feedback_store = FeedbackStore(path=tmp_path / "feedback" / "feedback.jsonl")
    job_store = JobStore(path=tmp_path / "jobs" / "jobs.jsonl")
    monkeypatch.setattr(feedback_api, "get_feedback_store", lambda: feedback_store)
    monkeypatch.setattr(feedback_api, "get_job_store", lambda: job_store)
    monkeypatch.setattr(jobs_api, "get_job_store", lambda: job_store)

"""Tests for admin job APIs and feedback job creation."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from data_platform.feedback.feedback_store import FeedbackStore
from data_platform.jobs.job_store import JobStore
from qa_ba.api_tests.auth_helpers import admin_headers


def test_queue_reindex_creates_jobs(monkeypatch, tmp_path: Path) -> None:
    feedback_store, job_store = install_temp_stores(monkeypatch, tmp_path)
    client = TestClient(app)
    headers = admin_headers(client)
    feedback_id = create_feedback(client)

    response = client.post(f"/api/admin/feedback/{feedback_id}/queue-reindex", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["queued"] is True
    assert len(body["job_ids"]) == 2
    jobs = {job.job_id: job for job in job_store.list_jobs(limit=10)}
    assert [jobs[job_id].job_type for job_id in body["job_ids"]] == ["reindex", "qa_eval"]
    assert feedback_store.get_feedback(feedback_id).status == "queued_for_reindex"


def test_list_jobs_works(monkeypatch, tmp_path: Path) -> None:
    _, job_store = install_temp_stores(monkeypatch, tmp_path)
    job_store.append_job(job_type="qa_eval", source="manual", payload={"test": True})
    client = TestClient(app)
    headers = admin_headers(client)

    response = client.get("/api/admin/jobs", headers=headers)

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["jobs"][0]["job_type"] == "qa_eval"


def test_run_next_handles_no_pending_jobs(monkeypatch, tmp_path: Path) -> None:
    install_temp_stores(monkeypatch, tmp_path)
    client = TestClient(app)
    headers = admin_headers(client)

    response = client.post("/api/admin/jobs/run-next?dry_run=true", headers=headers)

    assert response.status_code == 200
    assert response.json()["ran"] == 0
    assert response.json()["jobs"] == []


def test_retry_job_works(monkeypatch, tmp_path: Path) -> None:
    _, job_store = install_temp_stores(monkeypatch, tmp_path)
    job = job_store.append_job(job_type="qa_eval", source="manual")
    job_store.update_job_status(job_id=job.job_id, status="failed", error="boom")
    client = TestClient(app)
    headers = admin_headers(client)

    response = client.post(f"/api/admin/jobs/{job.job_id}/retry", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["error"] == ""


def test_queue_recrawl_creates_chained_jobs(monkeypatch, tmp_path: Path) -> None:
    feedback_store, job_store = install_temp_stores(monkeypatch, tmp_path)
    client = TestClient(app)
    headers = admin_headers(client)
    feedback_id = create_feedback(client)

    response = client.post(f"/api/admin/feedback/{feedback_id}/queue-recrawl", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["queued"] is True
    assert len(body["job_ids"]) == 4
    jobs = {job.job_id: job for job in job_store.list_jobs(limit=10)}
    assert [jobs[job_id].job_type for job_id in body["job_ids"]] == ["recrawl", "rebuild_features", "reindex", "qa_eval"]
    assert feedback_store.get_feedback(feedback_id).status == "queued_for_recrawl"


def install_temp_stores(monkeypatch, tmp_path: Path) -> tuple[FeedbackStore, JobStore]:
    from backend.app.api import feedback as feedback_api
    from backend.app.api import jobs as jobs_api

    feedback_store = FeedbackStore(path=tmp_path / "feedback" / "feedback.jsonl")
    job_store = JobStore(path=tmp_path / "jobs" / "jobs.jsonl")
    monkeypatch.setattr(feedback_api, "get_feedback_store", lambda: feedback_store)
    monkeypatch.setattr(feedback_api, "get_job_store", lambda: job_store)
    monkeypatch.setattr(jobs_api, "get_job_store", lambda: job_store)
    return feedback_store, job_store


def create_feedback(client: TestClient) -> str:
    response = client.post(
        "/api/feedback",
        json={
            "rating": "down",
            "reason": "missing_source",
            "query": "khoa học dữ liệu học những môn gì",
            "answer": "missing source",
            "intent": "institutional_rag",
            "route": ["rag_node"],
            "sources": [
                {
                    "source_url": "https://tuyensinh.hus.vnu.edu.vn/dai-hoc/nganh-hoc/toan-toan-ung-dung-va-tin-hoc/khoa-hoc-du-lieu"
                }
            ],
        },
    )
    assert response.status_code == 200
    return response.json()["feedback_id"]

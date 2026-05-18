"""Processing helpers for feedback records."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.feedback_schema import FeedbackStatus
from data_platform.feedback.feedback_store import FeedbackStore, feedback_record_to_eval_case
from data_platform.jobs.job_schema import JobRecord
from data_platform.jobs.job_store import JobStore


def promote_feedback_to_eval(
    *,
    feedback_id: str,
    store: FeedbackStore | None = None,
    eval_path: Path | None = None,
) -> tuple[bool, Path]:
    feedback_store = store or FeedbackStore()
    target = eval_path or Path("qa_ba/test_cases/feedback_eval_questions.jsonl")
    record = feedback_store.get_feedback(feedback_id)
    if record is None:
        return False, target

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(feedback_record_to_eval_case(record), ensure_ascii=False) + "\n")
    feedback_store.update_feedback(feedback_id=feedback_id, status="promoted_to_eval")
    return True, target


def queue_feedback_action(
    *,
    feedback_id: str,
    action: str,
    store: FeedbackStore | None = None,
    job_store: JobStore | None = None,
) -> tuple[bool, Path, FeedbackStatus, list[JobRecord]]:
    feedback_store = store or FeedbackStore()
    jobs = job_store or JobStore()
    record = feedback_store.get_feedback(feedback_id)
    if record is None:
        queue_name = "reindex_queue" if action == "reindex" else "recrawl_queue"
        return False, feedback_store.root / f"{queue_name}.jsonl", "queued_for_reindex", []

    if action == "reindex":
        status: FeedbackStatus = "queued_for_reindex"
        queue_name = "reindex_queue"
        created_jobs = [
            jobs.append_job(
                job_type="reindex",
                source="feedback",
                source_id=feedback_id,
                payload=feedback_payload(record),
            ),
            jobs.append_job(
                job_type="qa_eval",
                source="feedback",
                source_id=feedback_id,
                payload={"reason": record.reason},
            ),
        ]
    elif action == "recrawl":
        status = "queued_for_recrawl"
        queue_name = "recrawl_queue"
        created_jobs = [
            jobs.append_job(
                job_type="recrawl",
                source="feedback",
                source_id=feedback_id,
                payload=feedback_payload(record),
            ),
            jobs.append_job(
                job_type="rebuild_features",
                source="feedback",
                source_id=feedback_id,
                payload={"depends_on": "recrawl", "feedback_id": feedback_id},
            ),
            jobs.append_job(
                job_type="reindex",
                source="feedback",
                source_id=feedback_id,
                payload={"depends_on": "rebuild_features", "feedback_id": feedback_id},
            ),
            jobs.append_job(
                job_type="qa_eval",
                source="feedback",
                source_id=feedback_id,
                payload={"depends_on": "reindex", "feedback_id": feedback_id},
            ),
        ]
    else:
        raise ValueError(f"Unsupported feedback queue action: {action}")

    queued, path = feedback_store.append_queue_item(feedback_id=feedback_id, queue_name=queue_name)
    if queued:
        feedback_store.update_feedback(feedback_id=feedback_id, status=status)
    return queued, path, status, created_jobs


def feedback_payload(record) -> dict:
    source_url = ""
    for source in record.sources:
        if source.get("source_url"):
            source_url = str(source["source_url"])
            break
    return {
        "feedback_id": record.feedback_id,
        "query": record.query,
        "reason": record.reason,
        "intent": record.intent,
        "source_url": source_url,
        "sources": record.sources,
    }

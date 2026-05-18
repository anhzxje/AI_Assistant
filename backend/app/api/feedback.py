"""Feedback API for assistant quality review."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.services.auth.auth_service import get_current_user_optional, require_admin_user
from backend.app.services.auth.user_store import UserRecord
from backend.app.schemas.feedback_schema import (
    FeedbackListResponse,
    FeedbackRecord,
    FeedbackRequest,
    FeedbackSummaryResponse,
    FeedbackUpdateRequest,
    PromoteToEvalResponse,
    QueueActionResponse,
)
from data_platform.feedback.feedback_processor import promote_feedback_to_eval, queue_feedback_action
from data_platform.feedback.feedback_store import FeedbackStore
from data_platform.jobs.job_store import JobStore

router = APIRouter(tags=["feedback"])


@router.post("/api/feedback", response_model=FeedbackRecord)
def create_feedback(
    request: FeedbackRequest,
    user: UserRecord | None = Depends(get_current_user_optional),
) -> FeedbackRecord:
    if user is not None:
        request.user_id = user.user_id
    return get_feedback_store().add_feedback(request)


@router.get("/api/admin/feedback", response_model=FeedbackListResponse)
def list_feedback(
    _admin=Depends(require_admin_user),
    rating: str | None = Query(default=None),
    reason: str | None = Query(default=None),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    intent: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> FeedbackListResponse:
    records = get_feedback_store().list_feedback(
        rating=rating,
        reason=reason,
        status=status,
        severity=severity,
        intent=intent,
        limit=limit,
    )
    return FeedbackListResponse(count=len(records), feedback=records)


@router.get("/api/admin/feedback/summary", response_model=FeedbackSummaryResponse)
def feedback_summary(_admin=Depends(require_admin_user)) -> FeedbackSummaryResponse:
    return FeedbackSummaryResponse(**get_feedback_store().summary())


@router.patch("/api/admin/feedback/{feedback_id}", response_model=FeedbackRecord)
def update_feedback(feedback_id: str, request: FeedbackUpdateRequest, _admin=Depends(require_admin_user)) -> FeedbackRecord:
    record = get_feedback_store().update_feedback(
        feedback_id=feedback_id,
        status=request.status,
        admin_note=request.admin_note,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return record


@router.post("/api/admin/feedback/{feedback_id}/promote-to-eval", response_model=PromoteToEvalResponse)
def promote_feedback(feedback_id: str, _admin=Depends(require_admin_user)) -> PromoteToEvalResponse:
    promoted, path = promote_feedback_to_eval(feedback_id=feedback_id, store=get_feedback_store())
    if not promoted:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return PromoteToEvalResponse(feedback_id=feedback_id, eval_path=str(path), promoted=True)


@router.post("/api/admin/feedback/{feedback_id}/queue-reindex", response_model=QueueActionResponse)
def queue_reindex(feedback_id: str, _admin=Depends(require_admin_user)) -> QueueActionResponse:
    queued, path, status, jobs = queue_feedback_action(
        feedback_id=feedback_id,
        action="reindex",
        store=get_feedback_store(),
        job_store=get_job_store(),
    )
    if not queued:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return QueueActionResponse(
        feedback_id=feedback_id,
        queue_path=str(path),
        status=status,
        queued=True,
        job_ids=[job.job_id for job in jobs],
    )


@router.post("/api/admin/feedback/{feedback_id}/queue-recrawl", response_model=QueueActionResponse)
def queue_recrawl(feedback_id: str, _admin=Depends(require_admin_user)) -> QueueActionResponse:
    queued, path, status, jobs = queue_feedback_action(
        feedback_id=feedback_id,
        action="recrawl",
        store=get_feedback_store(),
        job_store=get_job_store(),
    )
    if not queued:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return QueueActionResponse(
        feedback_id=feedback_id,
        queue_path=str(path),
        status=status,
        queued=True,
        job_ids=[job.job_id for job in jobs],
    )


@lru_cache(maxsize=1)
def get_feedback_store() -> FeedbackStore:
    return FeedbackStore()


@lru_cache(maxsize=1)
def get_job_store() -> JobStore:
    return JobStore()

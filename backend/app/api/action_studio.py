"""Draft-only Action Studio APIs."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.schemas.action_studio_schema import (
    ActionDraftResponse,
    EmailDraftRequest,
    MeetingPrepRequest,
    RecentDraftsResponse,
    ReportDraftRequest,
    SlideDraftRequest,
)
from backend.app.services.action_studio.action_store import ActionDraftStore
from backend.app.services.action_studio.email_draft_generator import EmailDraftGenerator
from backend.app.services.action_studio.meeting_prep import MeetingPrepGenerator
from backend.app.services.action_studio.report_generator import ReportGenerator
from backend.app.services.action_studio.slide_generator import SlideGenerator
from backend.app.services.auth.auth_service import get_current_user
from backend.app.services.auth.user_store import UserRecord

router = APIRouter(tags=["action-studio"])


@router.post("/api/action-studio/meeting-prep", response_model=ActionDraftResponse)
def create_meeting_prep(request: MeetingPrepRequest, user: UserRecord = Depends(get_current_user)) -> ActionDraftResponse:
    draft = get_meeting_generator().generate(
        user_id=user.user_id,
        query=request.query,
        event_id=request.event_id,
        project_id=request.project_id,
        include_emails=request.include_emails,
        include_tasks=request.include_tasks,
    )
    return ActionDraftResponse(**draft.model_dump(mode="json"))


@router.post("/api/action-studio/report", response_model=ActionDraftResponse)
def create_report(request: ReportDraftRequest, user: UserRecord = Depends(get_current_user)) -> ActionDraftResponse:
    draft = get_report_generator().generate(
        user_id=user.user_id,
        period=request.period,
        style=request.style,
        project_id=request.project_id,
        role=user.role,
    )
    return ActionDraftResponse(**draft.model_dump(mode="json"))


@router.post("/api/action-studio/slides", response_model=ActionDraftResponse)
def create_slides(request: SlideDraftRequest, user: UserRecord = Depends(get_current_user)) -> ActionDraftResponse:
    draft = get_slide_generator().generate(
        user_id=user.user_id,
        topic=request.topic,
        source=request.source,
        slide_count=request.slide_count,
        format=request.format,
    )
    return ActionDraftResponse(**draft.model_dump(mode="json"))


@router.post("/api/action-studio/email-draft", response_model=ActionDraftResponse)
def create_email_draft(request: EmailDraftRequest, user: UserRecord = Depends(get_current_user)) -> ActionDraftResponse:
    draft = get_email_generator().generate(
        user_id=user.user_id,
        email_id=request.email_id,
        thread_id=request.thread_id,
        instruction=request.instruction,
        tone=request.tone,
        language=request.language,
    )
    return ActionDraftResponse(**draft.model_dump(mode="json"))


@router.get("/api/action-studio/recent", response_model=RecentDraftsResponse)
def recent_drafts(user: UserRecord = Depends(get_current_user)) -> RecentDraftsResponse:
    drafts = [ActionDraftResponse(**draft.model_dump(mode="json")) for draft in get_store().recent(user_id=user.user_id)]
    return RecentDraftsResponse(drafts=drafts, count=len(drafts))


@router.get("/api/action-studio/{draft_id}", response_model=ActionDraftResponse)
def get_draft(draft_id: str, user: UserRecord = Depends(get_current_user)) -> ActionDraftResponse:
    draft = get_store().get(user_id=user.user_id, draft_id=draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return ActionDraftResponse(**draft.model_dump(mode="json"))


@lru_cache(maxsize=1)
def get_store() -> ActionDraftStore:
    return ActionDraftStore()


@lru_cache(maxsize=1)
def get_meeting_generator() -> MeetingPrepGenerator:
    return MeetingPrepGenerator()


@lru_cache(maxsize=1)
def get_report_generator() -> ReportGenerator:
    return ReportGenerator()


@lru_cache(maxsize=1)
def get_slide_generator() -> SlideGenerator:
    return SlideGenerator()


@lru_cache(maxsize=1)
def get_email_generator() -> EmailDraftGenerator:
    return EmailDraftGenerator()


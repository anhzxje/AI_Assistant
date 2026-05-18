"""API schemas for draft-only Action Studio."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MeetingPrepRequest(BaseModel):
    query: str = Field(default="Chuẩn bị cho cuộc họp gần nhất", min_length=1)
    event_id: str | None = None
    project_id: str | None = None
    include_emails: bool = True
    include_tasks: bool = True


class ReportDraftRequest(BaseModel):
    period: Literal["today", "7d", "30d"] = "today"
    style: Literal["student", "admin", "research"] = "student"
    project_id: str | None = None


class SlideDraftRequest(BaseModel):
    topic: str = Field(min_length=1)
    source: Literal["latest_briefing", "project", "free_text"] = "latest_briefing"
    slide_count: int = Field(default=6, ge=3, le=12)
    format: Literal["marp_markdown"] = "marp_markdown"


class EmailDraftRequest(BaseModel):
    email_id: str | None = None
    thread_id: str | None = None
    instruction: str = Field(default="viết phản hồi lịch sự", min_length=1)
    tone: Literal["formal", "friendly", "short"] = "formal"
    language: Literal["vi", "en"] = "vi"


class ActionDraftResponse(BaseModel):
    draft_id: str
    user_id: str
    draft_type: str
    title: str
    content: str
    format: str
    sources: list[dict[str, Any]]
    created_at: str
    metadata: dict[str, Any]


class RecentDraftsResponse(BaseModel):
    drafts: list[ActionDraftResponse]
    count: int


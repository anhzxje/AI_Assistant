"""Schemas for draft-only Action Studio."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DraftType = Literal["meeting_prep", "exam_prep", "deadline_prep", "daily_plan", "report", "slides", "email_draft"]
DraftFormat = Literal["markdown", "text", "json"]


class SourceReference(BaseModel):
    source_type: str
    source_id: str | None = None
    title: str
    text: str = ""
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceBundle(BaseModel):
    user_id: str
    context: dict[str, Any] = Field(default_factory=dict)
    briefing: dict[str, Any] = Field(default_factory=dict)
    knowledge_summary: dict[str, Any] = Field(default_factory=dict)
    selected: dict[str, Any] = Field(default_factory=dict)
    gmail_messages: list[dict[str, Any]] = Field(default_factory=list)
    calendar_events: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionDraft(BaseModel):
    draft_id: str
    user_id: str
    draft_type: DraftType
    title: str
    content: str
    format: DraftFormat
    sources: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

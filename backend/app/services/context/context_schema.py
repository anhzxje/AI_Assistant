"""Schemas for proactive personal context."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ContextSourceItem(BaseModel):
    source_type: str
    source_id: str
    title: str
    text: str = ""
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextTask(BaseModel):
    task_id: str
    title: str
    priority: str = "medium"
    due_date: str | None = None
    source_type: str
    source_id: str
    score: float = 0.0


class ContextProject(BaseModel):
    project_id: str
    name: str
    keywords: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    update_count: int = 0
    score: float = 0.0


class ContextPriority(BaseModel):
    priority_id: str
    title: str
    reason: str
    score: float
    source_type: str
    source_id: str
    suggested_action: str


class PersonalContext(BaseModel):
    user_id: str
    generated_at: str
    time_window: str = "today"
    people: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[ContextProject] = Field(default_factory=list)
    tasks: list[ContextTask] = Field(default_factory=list)
    deadlines: list[dict[str, Any]] = Field(default_factory=list)
    meetings: list[dict[str, Any]] = Field(default_factory=list)
    important_emails: list[dict[str, Any]] = Field(default_factory=list)
    noise_summary: dict[str, Any] = Field(default_factory=dict)
    priorities: list[ContextPriority] = Field(default_factory=list)
    knowledge_gaps: list[dict[str, Any]] = Field(default_factory=list)
    source_items: list[ContextSourceItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

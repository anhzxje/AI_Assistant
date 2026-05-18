"""Pydantic schemas for personal memory and task APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    memory_id: str
    user_id: str
    memory_type: str
    content: str
    importance: float = Field(ge=0.0, le=1.0)
    source: str
    created_at: datetime
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskRecord(BaseModel):
    task_id: str
    user_id: str
    title: str
    due_date: date | None = None
    priority: str = "medium"
    status: str = "open"
    source_text: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RememberRequest(BaseModel):
    text: str = Field(min_length=1)
    user_id: str = "default"
    session_id: str | None = None
    memory_type: str | None = None
    importance: float = Field(default=0.6, ge=0.0, le=1.0)


class RememberResponse(BaseModel):
    saved_memories: list[MemoryRecord]
    extracted_tasks: list[TaskRecord]
    semantic_indexed: int


class MemoryQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    user_id: str = "default"
    session_id: str | None = None
    limit: int = Field(default=8, ge=1, le=30)


class MemoryQueryResponse(BaseModel):
    long_term_memories: list[MemoryRecord]
    semantic_memories: list[MemoryRecord]
    open_tasks: list[TaskRecord]
    recent_turns: list[dict[str, Any]]


class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1)
    user_id: str = "default"
    due_date: date | None = None
    priority: str = "medium"
    status: str = "open"
    source_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateTaskRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    due_date: date | None = None
    priority: str | None = None
    status: str | None = None
    metadata: dict[str, Any] | None = None


class MemorySummaryResponse(BaseModel):
    long_term_memories_count: int
    tasks_count: int
    recent_session_count: int
    storage_mode: dict[str, str]
    recent_memories: list[MemoryRecord]
    upcoming_tasks: list[TaskRecord]


class DeleteResponse(BaseModel):
    deleted: bool
    id: str

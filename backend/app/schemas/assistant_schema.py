"""Schemas for assistant orchestration API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AssistantChatRequest(BaseModel):
    user_id: str = "default"
    session_id: str | None = None
    message: str = Field(min_length=1)
    include_memory: bool = True
    use_mock_google: bool = False
    role: str | None = None


class AssistantChatResponse(BaseModel):
    answer: str
    intent: str
    sources: list[dict[str, Any]]
    actions: list[str]
    memory_used: bool
    metadata: dict[str, Any]

"""Schemas for conversation state persisted by the assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ConversationRole = Literal["user", "assistant", "system", "tool"]


class ConversationMessage(BaseModel):
    message_id: str
    user_id: str
    session_id: str
    role: ConversationRole
    content: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationSession(BaseModel):
    user_id: str
    session_id: str
    message_count: int
    last_message_at: datetime | None = None
    last_topic_hint: str | None = None

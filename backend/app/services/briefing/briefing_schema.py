"""Schemas for smart proactive briefings."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SmartBriefing(BaseModel):
    briefing_id: str
    user_id: str
    generated_at: str
    headline: str
    morning_report: str
    top_priorities: list[dict[str, Any]] = Field(default_factory=list)
    upcoming_events: list[dict[str, Any]] = Field(default_factory=list)
    important_emails: list[dict[str, Any]] = Field(default_factory=list)
    suggested_actions: list[dict[str, Any]] = Field(default_factory=list)
    project_updates: list[dict[str, Any]] = Field(default_factory=list)
    ignored_noise_count: int = 0
    sources: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

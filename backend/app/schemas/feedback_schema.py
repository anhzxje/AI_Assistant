"""Schemas for assistant feedback APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


FeedbackRating = Literal["up", "down"]
FeedbackReason = Literal[
    "wrong_answer",
    "outdated_data",
    "missing_source",
    "bad_citation",
    "bad_asr",
    "bad_tts",
    "irrelevant_retrieval",
    "too_slow",
    "other",
]
FeedbackStatus = Literal[
    "new",
    "reviewed",
    "promoted_to_eval",
    "queued_for_recrawl",
    "queued_for_reindex",
    "ignored",
]
FeedbackSeverity = Literal["low", "medium", "high"]


class FeedbackDiagnostics(BaseModel):
    source_count: int = 0
    has_citations: bool = False
    latency_ms: int = 0
    retrieval_scores: list[float] = Field(default_factory=list)
    suspected_issue: str = ""


class FeedbackRequest(BaseModel):
    user_id: str = "default"
    session_id: str | None = None
    message_id: str | None = None
    query: str = ""
    answer: str = ""
    intent: str = ""
    route: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    rating: FeedbackRating
    reason: FeedbackReason | None = None
    correction: str | None = None
    diagnostics: FeedbackDiagnostics | None = None

    @model_validator(mode="after")
    def require_reason_for_downvote(self) -> "FeedbackRequest":
        if self.rating == "down" and self.reason is None:
            raise ValueError("reason is required for downvote feedback")
        return self


class FeedbackRecord(BaseModel):
    feedback_id: str
    user_id: str = "default"
    session_id: str | None = None
    message_id: str | None = None
    query: str = ""
    answer: str = ""
    intent: str = ""
    route: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    rating: FeedbackRating
    reason: FeedbackReason = "other"
    correction: str | None = None
    status: FeedbackStatus = "new"
    severity: FeedbackSeverity = "low"
    created_at: datetime
    updated_at: datetime | None = None
    admin_note: str = ""
    diagnostics: FeedbackDiagnostics = Field(default_factory=FeedbackDiagnostics)


class FeedbackUpdateRequest(BaseModel):
    status: FeedbackStatus | None = None
    admin_note: str | None = None


class FeedbackListResponse(BaseModel):
    count: int
    feedback: list[FeedbackRecord]


class FeedbackSummaryResponse(BaseModel):
    total: int
    by_rating: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int]
    by_reason: dict[str, int]
    by_severity: dict[str, int]
    by_intent: dict[str, int]
    top_problem_sources: list[dict[str, Any]]
    top_failed_queries: list[dict[str, Any]]
    recommended_actions: list[str]


class PromoteToEvalResponse(BaseModel):
    feedback_id: str
    eval_path: str
    promoted: bool


class QueueActionResponse(BaseModel):
    feedback_id: str
    queue_path: str
    status: FeedbackStatus
    queued: bool
    job_ids: list[str] = Field(default_factory=list)

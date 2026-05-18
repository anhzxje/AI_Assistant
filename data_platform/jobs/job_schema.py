"""Schemas for local executable admin jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


JobType = Literal["recrawl", "reindex", "rebuild_features", "qa_eval"]
JobStatus = Literal["pending", "running", "success", "failed", "skipped"]
JobSource = Literal["feedback", "manual", "system"]


class JobRecord(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus = "pending"
    source: JobSource = "manual"
    source_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)


class JobListResponse(BaseModel):
    count: int
    jobs: list[JobRecord]


class JobRunResponse(BaseModel):
    ran: int
    jobs: list[JobRecord]
    message: str

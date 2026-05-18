"""Schemas for read-only Google personal connectors."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GoogleStatusResponse(BaseModel):
    credentials_available: bool
    google_libraries_available: bool
    mode: str
    client_secret_path: str | None
    scopes: list[str]
    read_only: bool = True


class GoogleIntegrationStatusResponse(BaseModel):
    google_login_configured: bool
    google_login_email: str | None = None
    gmail_connected: bool = False
    calendar_connected: bool = False
    gmail_account_email: str | None = None
    calendar_account_email: str | None = None
    gmail_account_mismatch: bool = False
    calendar_account_mismatch: bool = False
    gmail_last_sync_at: str | None = None
    calendar_last_sync_at: str | None = None
    required_scopes: dict[str, list[str]]


class GmailSyncRequest(BaseModel):
    user_id: str = "default"
    max_results: int = Field(default=100, ge=1, le=2000)
    use_mock: bool = False
    scenario: str | None = None
    range: str | None = Field(default="90d", pattern="^(7d|30d|90d|1y|all_recent)$")
    query: str = "newer_than:90d"
    include_read: bool = True
    include_unread: bool = True
    include_spam_trash: bool = False


class CalendarSyncRequest(BaseModel):
    user_id: str = "default"
    range: str | None = Field(default="7d", pattern="^(7d|30d|90d|1y)$")
    days_ahead: int = Field(default=7, ge=0, le=365)
    start_date: str | None = None
    end_date: str | None = None
    calendar_ids: list[str] = Field(default_factory=list)
    include_all_calendars: bool = False
    include_holidays: bool = False
    use_mock: bool = False
    scenario: str | None = None
    include_cancelled: bool = False


class SyncResponse(BaseModel):
    user_id: str
    mode: str
    raw_path: str
    processed_path: str
    features_path: str | None = None
    records_synced: int
    connected: bool = True
    message: str | None = None
    source_mode: str = "mock"
    metadata: dict[str, Any] = Field(default_factory=dict)
    calendar_connected: bool | None = None
    calendar_count: int | None = None
    calendars: list[dict[str, Any]] | None = None
    events_count: int | None = None
    today_count: int | None = None
    date_range: dict[str, str] | None = None
    events: list[dict[str, Any]] | None = None


class CalendarListResponse(BaseModel):
    connected: bool
    calendars: list[dict[str, Any]] = Field(default_factory=list)


class GmailSummaryResponse(BaseModel):
    user_id: str
    total_messages: int
    unread_count: int
    important_count: int
    noise_count: int = 0
    top_senders: dict[str, int]
    recent_messages: list[dict[str, Any]]
    source_mode: str = "not_connected"


class CalendarTodayResponse(BaseModel):
    user_id: str
    date: str
    events: list[dict[str, Any]]
    source_mode: str = "not_connected"


class DailyBriefingResponse(BaseModel):
    user_id: str
    date: str
    summary: str = ""
    important_emails: list[dict[str, Any]] = Field(default_factory=list)
    ignored_noise_count: int = 0
    today_events: list[dict[str, Any]]
    email_summary: dict[str, Any]
    extracted_email_tasks: list[dict[str, Any]]
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    task_memory: list[dict[str, Any]]
    priorities: list[str]
    institutional_reminders: list[dict[str, str]]
    generated_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

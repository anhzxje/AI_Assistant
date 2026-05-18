"""Read-only Google Calendar connector with mock fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.services.connectors.google_auth import GoogleAuthManager
from backend.app.services.connectors.calendar_real_connector import list_calendar_readonly, sync_calendar_readonly
from backend.app.services.connectors.scenario_loader import load_calendar_scenario, resolve_scenario
from backend.app.services.integrations.google_token_store import GoogleTokenStore


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "calendar_mock.json"


@dataclass(frozen=True)
class CalendarSyncResult:
    user_id: str
    mode: str
    events: list[dict[str, Any]]
    calendars: list[dict[str, Any]] | None = None
    available_calendars: list[dict[str, Any]] | None = None
    date_range: dict[str, str] | None = None


class CalendarConnector:
    def __init__(self, auth_manager: GoogleAuthManager | None = None, token_store: GoogleTokenStore | None = None) -> None:
        self.auth_manager = auth_manager or GoogleAuthManager()
        self.token_store = token_store or GoogleTokenStore()

    def fetch_events(
        self,
        *,
        user_id: str,
        days_ahead: int = 7,
        use_mock: bool = False,
        scenario: str | None = None,
        include_cancelled: bool = False,
        start_date: str | None = None,
        end_date: str | None = None,
        calendar_ids: list[str] | None = None,
        include_all_calendars: bool = False,
        include_holidays: bool = False,
    ) -> CalendarSyncResult:
        if use_mock:
            resolved = resolve_scenario(user_id, scenario)
            if resolved:
                return CalendarSyncResult(user_id=user_id, mode=f"mock:{resolved}", events=load_calendar_scenario(resolved))
            events = load_mock_events()
            return CalendarSyncResult(user_id=user_id, mode="mock", events=events)

        if not self.token_store.is_connected(user_id, "calendar"):
            return CalendarSyncResult(user_id=user_id, mode="not_connected", events=[])
        result = sync_calendar_readonly(
            user_id=user_id,
            days_ahead=days_ahead,
            token_store=self.token_store,
            include_cancelled=include_cancelled,
            start_date=start_date,
            end_date=end_date,
            calendar_ids=calendar_ids,
            include_all_calendars=include_all_calendars,
            include_holidays=include_holidays,
        )
        if isinstance(result, list):
            return CalendarSyncResult(user_id=user_id, mode="real", events=result)
        return CalendarSyncResult(
            user_id=user_id,
            mode="real",
            events=result.get("events", []),
            calendars=result.get("calendars", []),
            available_calendars=result.get("available_calendars", []),
            date_range=result.get("date_range"),
        )

    def list_calendars(self, *, user_id: str) -> list[dict[str, Any]]:
        if not self.token_store.is_connected(user_id, "calendar"):
            return []
        return list_calendar_readonly(user_id=user_id, token_store=self.token_store)


def load_mock_events() -> list[dict[str, Any]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

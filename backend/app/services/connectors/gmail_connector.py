"""Read-only Gmail connector with mock fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.services.connectors.google_auth import GoogleAuthManager
from backend.app.services.connectors.gmail_real_connector import sync_gmail_readonly
from backend.app.services.connectors.scenario_loader import load_gmail_scenario, resolve_scenario
from backend.app.services.integrations.google_token_store import GoogleTokenStore


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gmail_mock.json"


@dataclass(frozen=True)
class GmailSyncResult:
    user_id: str
    mode: str
    messages: list[dict[str, Any]]


class GmailConnector:
    def __init__(self, auth_manager: GoogleAuthManager | None = None, token_store: GoogleTokenStore | None = None) -> None:
        self.auth_manager = auth_manager or GoogleAuthManager()
        self.token_store = token_store or GoogleTokenStore()

    def fetch_messages(
        self,
        *,
        user_id: str,
        max_results: int = 100,
        use_mock: bool = False,
        scenario: str | None = None,
        query: str = "newer_than:90d",
        include_spam_trash: bool = False,
    ) -> GmailSyncResult:
        if use_mock:
            resolved = resolve_scenario(user_id, scenario)
            if resolved:
                messages = load_gmail_scenario(resolved, max_results=max_results)
                return GmailSyncResult(user_id=user_id, mode=f"mock:{resolved}", messages=messages)
            messages = load_mock_messages(max_results=max_results)
            return GmailSyncResult(user_id=user_id, mode="mock", messages=messages)

        if not self.token_store.is_connected(user_id, "gmail"):
            return GmailSyncResult(user_id=user_id, mode="not_connected", messages=[])
        messages = sync_gmail_readonly(
            user_id=user_id,
            max_results=max_results,
            token_store=self.token_store,
            query=query,
            include_spam_trash=include_spam_trash,
        )
        return GmailSyncResult(user_id=user_id, mode="real", messages=messages)


def load_mock_messages(*, max_results: int) -> list[dict[str, Any]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))[:max_results]


def header_value(message: dict[str, Any], name: str) -> str:
    direct_keys = {
        "from": "from",
        "to": "to",
        "subject": "subject",
        "date": "date",
    }
    direct_key = direct_keys.get(name.lower())
    if direct_key and message.get(direct_key):
        return str(message.get(direct_key) or "")
    headers = ((message.get("payload") or {}).get("headers") or [])
    for header in headers:
        if str(header.get("name", "")).lower() == name.lower():
            return str(header.get("value") or "")
    return ""

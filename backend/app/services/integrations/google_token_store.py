"""Local token storage for read-only Google integrations.

Tokens are stored under data/personal_memory, which is gitignored. This module
never logs token values and only exposes status metadata needed by the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

import httpx

from backend.app.config import get_backend_settings

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
VALID_INTEGRATIONS = {"gmail", "calendar"}


@dataclass(frozen=True)
class GoogleTokenStatus:
    connected: bool
    google_account_email: str | None = None
    scope: str | None = None
    expires_at: str | None = None
    refreshable: bool = False
    connected_at: str | None = None


class GoogleTokenStore:
    def __init__(self) -> None:
        settings = get_backend_settings()
        self.settings = settings
        self.root = settings.data_settings.resolved_data_root / "personal_memory" / "google_tokens"

    def status(self, user_id: str, integration: str) -> GoogleTokenStatus:
        token = self.load_token(user_id, integration)
        if not token:
            return GoogleTokenStatus(connected=False)
        return GoogleTokenStatus(
            connected=True,
            google_account_email=token.get("google_account_email"),
            scope=token.get("scope"),
            expires_at=token.get("expires_at"),
            refreshable=bool(token.get("refresh_token")),
            connected_at=token.get("connected_at"),
        )

    def is_connected(self, user_id: str, integration: str) -> bool:
        return self.status(user_id, integration).connected

    def save_token(self, user_id: str, integration: str, token: dict[str, Any], *, google_account_email: str | None = None) -> dict[str, Any]:
        integration = validate_integration(integration)
        now = datetime.now(timezone.utc)
        existing = self.load_token(user_id, integration) or {}
        expires_in = int(token.get("expires_in") or 3600)
        payload = {
            "access_token": token.get("access_token"),
            "refresh_token": token.get("refresh_token") or existing.get("refresh_token"),
            "expires_at": (now + timedelta(seconds=max(0, expires_in - 60))).isoformat(),
            "scope": token.get("scope") or existing.get("scope") or "",
            "token_type": token.get("token_type") or existing.get("token_type") or "Bearer",
            "google_account_email": google_account_email or existing.get("google_account_email"),
            "connected_at": existing.get("connected_at") or now.isoformat(),
            "updated_at": now.isoformat(),
            "refreshable": bool(token.get("refresh_token") or existing.get("refresh_token")),
        }
        self._path(user_id, integration).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def load_token(self, user_id: str, integration: str) -> dict[str, Any] | None:
        path = self._path(user_id, validate_integration(integration))
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def delete_token(self, user_id: str, integration: str) -> None:
        path = self._path(user_id, validate_integration(integration))
        if path.exists():
            path.unlink()

    def refresh_if_needed(self, user_id: str, integration: str) -> dict[str, Any] | None:
        token = self.load_token(user_id, integration)
        if not token:
            return None
        expires_at = parse_datetime(token.get("expires_at"))
        if expires_at and expires_at > datetime.now(timezone.utc):
            return token
        refresh_token = token.get("refresh_token")
        if not refresh_token:
            return None
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15.0,
        )
        response.raise_for_status()
        return self.save_token(
            user_id,
            integration,
            response.json(),
            google_account_email=token.get("google_account_email"),
        )

    def _path(self, user_id: str, integration: str) -> Path:
        safe_user = "".join(ch for ch in user_id if ch.isalnum() or ch in ("-", "_")) or "unknown"
        path = self.root / safe_user / f"{integration}_token.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def validate_integration(integration: str) -> str:
    if integration not in VALID_INTEGRATIONS:
        raise ValueError("unsupported_google_integration")
    return integration


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

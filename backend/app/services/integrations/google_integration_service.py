"""High-level Google integration status and disconnect operations."""

from __future__ import annotations

from backend.app.services.auth.google_oauth import GOOGLE_LOGIN_SCOPES, GoogleOAuthService
from backend.app.services.connectors.google_auth import CALENDAR_READONLY_SCOPE, GMAIL_READONLY_SCOPE
from backend.app.config import get_backend_settings
from backend.app.services.connectors.personal_ingestion import read_sync_status
from backend.app.services.integrations.google_token_store import GoogleTokenStore


class GoogleIntegrationService:
    def __init__(self, token_store: GoogleTokenStore | None = None) -> None:
        self.token_store = token_store or GoogleTokenStore()

    def status(self, user_id: str, google_login_email: str | None = None) -> dict:
        gmail = self.token_store.status(user_id, "gmail")
        calendar = self.token_store.status(user_id, "calendar")
        data_root = get_backend_settings().data_settings.resolved_data_root
        gmail_sync = read_sync_status(data_root, user_id, "gmail") or {}
        calendar_sync = read_sync_status(data_root, user_id, "calendar") or {}
        return {
            "google_login_configured": GoogleOAuthService().configured,
            "google_login_email": google_login_email,
            "gmail_connected": gmail.connected,
            "calendar_connected": calendar.connected,
            "gmail_account_email": gmail.google_account_email,
            "calendar_account_email": calendar.google_account_email,
            "gmail_account_mismatch": account_mismatch(google_login_email, gmail.google_account_email),
            "calendar_account_mismatch": account_mismatch(google_login_email, calendar.google_account_email),
            "gmail_last_sync_at": gmail_sync.get("synced_at"),
            "calendar_last_sync_at": calendar_sync.get("synced_at"),
            "required_scopes": {
                "login": GOOGLE_LOGIN_SCOPES,
                "gmail_readonly": [GMAIL_READONLY_SCOPE],
                "calendar_readonly": [CALENDAR_READONLY_SCOPE],
            },
        }

    def disconnect(self, user_id: str, integration: str) -> dict:
        self.token_store.delete_token(user_id, integration)
        return {"ok": True, "integration": integration, "connected": False}


def account_mismatch(expected: str | None, actual: str | None) -> bool:
    return bool(expected and actual and expected.strip().lower() != actual.strip().lower())

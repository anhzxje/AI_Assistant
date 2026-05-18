"""OAuth flow for optional read-only Google integrations."""

from __future__ import annotations

from dataclasses import dataclass
from time import time
import secrets
from urllib.parse import urlencode

import httpx

from backend.app.config import get_backend_settings
from backend.app.services.connectors.google_auth import CALENDAR_READONLY_SCOPE, GMAIL_READONLY_SCOPE

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
STATE_TTL_SECONDS = 600

INTEGRATION_SCOPES = {
    "gmail": [GMAIL_READONLY_SCOPE],
    "calendar": [CALENDAR_READONLY_SCOPE],
}

_STATE_STORE: dict[str, dict] = {}


@dataclass(frozen=True)
class IntegrationState:
    user_id: str
    integration: str
    expires_at: float


class GoogleIntegrationOAuthService:
    def __init__(self) -> None:
        self.settings = get_backend_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.google_client_id and self.settings.google_client_secret)

    def redirect_uri(self, integration: str) -> str:
        if integration == "gmail":
            return self.settings.google_gmail_redirect_uri
        if integration == "calendar":
            return self.settings.google_calendar_redirect_uri
        raise ValueError("unsupported_google_integration")

    def create_state(self, *, user_id: str, integration: str) -> str:
        if integration not in INTEGRATION_SCOPES:
            raise ValueError("unsupported_google_integration")
        cleanup_expired_states()
        state = secrets.token_urlsafe(32)
        _STATE_STORE[state] = {
            "user_id": user_id,
            "integration": integration,
            "expires_at": time() + STATE_TTL_SECONDS,
        }
        return state

    def consume_state(self, state: str, integration: str) -> IntegrationState | None:
        cleanup_expired_states()
        payload = _STATE_STORE.pop(state, None)
        if not payload or payload.get("integration") != integration:
            return None
        return IntegrationState(
            user_id=str(payload["user_id"]),
            integration=str(payload["integration"]),
            expires_at=float(payload["expires_at"]),
        )

    def authorization_url(self, *, state: str, integration: str, login_hint: str | None = None, force_consent: bool = True) -> str:
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.redirect_uri(integration),
            "response_type": "code",
            "scope": " ".join(INTEGRATION_SCOPES[integration]),
            "state": state,
            "access_type": "offline",
            "include_granted_scopes": "true",
        }
        if login_hint:
            params["login_hint"] = login_hint
        if force_consent:
            params["prompt"] = "consent"
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, *, code: str, integration: str) -> dict:
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "redirect_uri": self.redirect_uri(integration),
                "grant_type": "authorization_code",
            },
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()

    def account_email(self, access_token: str) -> str | None:
        try:
            response = httpx.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            if response.status_code >= 400:
                return None
            email = str(response.json().get("email") or "").strip().lower()
            return email or None
        except Exception:
            return None


def cleanup_expired_states() -> None:
    now = time()
    expired = [state for state, payload in _STATE_STORE.items() if float(payload.get("expires_at", 0)) < now]
    for state in expired:
        _STATE_STORE.pop(state, None)

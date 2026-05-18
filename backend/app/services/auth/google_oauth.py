"""Google OpenID login flow.

This service intentionally requests only identity scopes. Gmail and Calendar
authorization stay in a separate connector flow so sign-in never grants data access.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import time
import secrets
from urllib.parse import urlencode

import httpx

from backend.app.config import get_backend_settings


GOOGLE_LOGIN_SCOPES = ["openid", "email", "profile"]
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
STATE_TTL_SECONDS = 600

_STATE_STORE: dict[str, float] = {}


@dataclass(frozen=True)
class GoogleProfile:
    email: str
    display_name: str
    sub: str | None = None


class GoogleOAuthService:
    def __init__(self) -> None:
        self.settings = get_backend_settings()

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.google_client_id
            and self.settings.google_client_secret
            and self.settings.google_redirect_uri
        )

    def create_state(self) -> str:
        cleanup_expired_states()
        state = secrets.token_urlsafe(32)
        _STATE_STORE[state] = time() + STATE_TTL_SECONDS
        return state

    def validate_state(self, state: str) -> bool:
        cleanup_expired_states()
        expires_at = _STATE_STORE.pop(state, None)
        return bool(expires_at and expires_at >= time())

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_LOGIN_SCOPES),
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict:
        if not self.configured:
            raise RuntimeError("google_oauth_not_configured")
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "redirect_uri": self.settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()

    def profile_from_tokens(self, tokens: dict) -> GoogleProfile:
        id_token = tokens.get("id_token")
        if id_token:
            response = httpx.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token}, timeout=10.0)
            response.raise_for_status()
            payload = response.json()
            if payload.get("aud") != self.settings.google_client_id:
                raise ValueError("google_id_token_audience_mismatch")
            return profile_from_payload(payload)

        access_token = tokens.get("access_token")
        if not access_token:
            raise ValueError("google_token_missing_identity")
        response = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        response.raise_for_status()
        return profile_from_payload(response.json())


def profile_from_payload(payload: dict) -> GoogleProfile:
    email = str(payload.get("email") or "").strip().lower()
    if not email:
        raise ValueError("google_profile_missing_email")
    name = str(payload.get("name") or payload.get("given_name") or email.split("@", 1)[0]).strip()
    return GoogleProfile(email=email, display_name=name, sub=str(payload.get("sub") or "") or None)


def cleanup_expired_states() -> None:
    now = time()
    expired = [state for state, expires_at in _STATE_STORE.items() if expires_at < now]
    for state in expired:
        _STATE_STORE.pop(state, None)

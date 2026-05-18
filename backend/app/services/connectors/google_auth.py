"""Read-only Google auth boundary.

This module never writes credentials and never requests write scopes. When OAuth
credentials are missing or Google client libraries are not installed, callers
fall back to fixture data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.app.config import get_backend_settings


GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


@dataclass(frozen=True)
class GoogleAuthStatus:
    credentials_available: bool
    google_libraries_available: bool
    mode: str
    client_secret_path: str | None
    scopes: list[str]


class GoogleAuthManager:
    def __init__(self) -> None:
        self.settings = get_backend_settings()
        self.client_secret_path = (
            Path(self.settings.google_client_secret_path).expanduser()
            if self.settings.google_client_secret_path
            else None
        )

    def status(self) -> GoogleAuthStatus:
        credentials_available = bool(self.client_secret_path and self.client_secret_path.exists())
        libraries_available = google_libraries_available()
        mode = "oauth_readonly" if credentials_available and libraries_available else "mock_fallback"
        return GoogleAuthStatus(
            credentials_available=credentials_available,
            google_libraries_available=libraries_available,
            mode=mode,
            client_secret_path=str(self.client_secret_path) if self.client_secret_path else None,
            scopes=[GMAIL_READONLY_SCOPE, CALENDAR_READONLY_SCOPE],
        )

    def service_available(self) -> bool:
        current = self.status()
        return current.credentials_available and current.google_libraries_available


def google_libraries_available() -> bool:
    try:
        import google.oauth2.credentials  # noqa: F401
        import googleapiclient.discovery  # noqa: F401

        return True
    except Exception:
        return False

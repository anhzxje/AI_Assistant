"""Tests for Google OpenID login scaffolding."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from backend.app.config import get_backend_settings
from backend.app.main import app
from backend.app.services.auth.user_store import UserRecord, UserStore
from qa_ba.api_tests.auth_helpers import admin_headers, user_headers


def test_google_login_status_unconfigured(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    get_backend_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/api/auth/google/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["scopes"] == ["openid", "email", "profile"]


def test_google_login_start_rejects_when_unconfigured(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    get_backend_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/api/auth/google/start", follow_redirects=False)

    assert response.status_code == 503
    assert "Google Login" in response.json()["detail"]


def test_google_login_status_configured_when_env_present(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/google/callback")
    get_backend_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/api/auth/google/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["scopes"] == ["openid", "email", "profile"]
    assert body["redirect_uri"] == "http://127.0.0.1:8000/api/auth/google/callback"


def test_google_login_start_uses_identity_scopes_only(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/google/callback")
    get_backend_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/api/auth/google/start", follow_redirects=False)

    assert response.status_code == 307
    location = response.headers["location"]
    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert params["redirect_uri"] == ["http://127.0.0.1:8000/api/auth/google/callback"]
    assert params["scope"] == ["openid email profile"]
    assert "https://www.googleapis.com/auth/gmail.readonly" not in params["scope"][0]
    assert "https://www.googleapis.com/auth/calendar.readonly" not in params["scope"][0]
    assert params.get("state", [""])[0]


def test_google_integrations_status_separates_login_and_connectors(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    get_backend_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/api/integrations/google/status", headers=user_headers(client))

    assert response.status_code == 200
    body = response.json()
    assert body["google_login_configured"] is False
    assert body["gmail_connected"] is False
    assert body["calendar_connected"] is False
    assert body["required_scopes"]["login"] == ["openid", "email", "profile"]
    assert "https://www.googleapis.com/auth/gmail.readonly" in body["required_scopes"]["gmail_readonly"]
    assert "https://www.googleapis.com/auth/calendar.readonly" in body["required_scopes"]["calendar_readonly"]


def test_google_created_user_defaults_to_user_role(tmp_path: Path) -> None:
    store = UserStore(path=tmp_path / "users.jsonl")

    user = store.upsert_google_user(
        email="student@example.com",
        display_name="Người dùng Google",
        google_sub="google-sub-123",
    )

    assert user.role == "user"
    assert user.email == "student@example.com"
    assert user.metadata["auth_provider"] == "google"
    assert store.verify_credentials("student@example.com", "anything") is None


def test_google_login_does_not_promote_existing_admin(tmp_path: Path) -> None:
    store = UserStore(path=tmp_path / "users.jsonl")
    admin = UserRecord(
        user_id="local-admin",
        email="admin@example.com",
        display_name="Local Admin",
        role="admin",
        password_hash="local-only",
        created_at=datetime.now(timezone.utc),
        metadata={"seeded": True},
    )
    store._write_users([admin])

    try:
        store.upsert_google_user("admin@example.com", "Google Admin", "sub")
    except ValueError as exc:
        assert str(exc) == "google_login_cannot_grant_admin"
    else:
        raise AssertionError("Google login must not grant admin role")


def test_local_user_and_admin_auth_still_work() -> None:
    client = TestClient(app)

    assert client.get("/api/auth/me", headers=user_headers(client)).json()["user"]["role"] == "user"
    assert client.get("/api/auth/me", headers=admin_headers(client)).json()["user"]["role"] == "admin"

"""Tests for Google integration account hint and mismatch protection."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.auth.user_store import UserRecord
from backend.app.services.integrations.google_oauth_service import GoogleIntegrationOAuthService
from qa_ba.api_tests.auth_helpers import user_headers
from qa_ba.api_tests.test_google_integrations import configure_google_env


def test_oauth_url_includes_login_hint_for_google_user(monkeypatch) -> None:
    configure_google_env(monkeypatch)
    client = TestClient(app)

    monkeypatch.setattr(
        "backend.app.api.google.expected_google_email",
        lambda user: "iron031.man@gmail.com",
    )

    response = client.get("/api/integrations/google/gmail/start-url", headers=user_headers(client))

    assert response.status_code == 200
    params = parse_qs(urlparse(response.json()["url"]).query)
    assert params["login_hint"] == ["iron031.man@gmail.com"]
    assert params["scope"] == ["https://www.googleapis.com/auth/gmail.readonly"]


def test_google_account_mismatch_is_rejected(monkeypatch) -> None:
    configure_google_env(monkeypatch)
    state = GoogleIntegrationOAuthService().create_state(user_id="google-user", integration="gmail")
    expected_user = UserRecord(
        user_id="google-user",
        email="iron031.man@gmail.com",
        display_name="Iron",
        role="user",
        password_hash="",
        created_at="2026-05-16T00:00:00+00:00",
        metadata={"auth_provider": "google", "google_email": "iron031.man@gmail.com"},
    )

    monkeypatch.setattr("backend.app.api.google.get_user_for_callback", lambda user_id: expected_user)
    monkeypatch.setattr("backend.app.services.integrations.google_oauth_service.GoogleIntegrationOAuthService.exchange_code", lambda self, code, integration: {"access_token": "fake", "expires_in": 3600})
    monkeypatch.setattr("backend.app.services.integrations.google_oauth_service.GoogleIntegrationOAuthService.account_email", lambda self, access_token: "other@example.com")

    client = TestClient(app)
    response = client.get(f"/api/integrations/google/gmail/callback?code=fake-code&state={state}", follow_redirects=False)

    assert response.status_code in {307, 302}
    assert "google" in response.headers["location"].lower()
    assert "iron031.man%40gmail.com" in response.headers["location"]

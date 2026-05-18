"""Tests for separate read-only Gmail/Calendar OAuth integration flows."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse
import uuid

from fastapi.testclient import TestClient

from backend.app.config import get_backend_settings
from backend.app.main import app
from backend.app.services.integrations.google_token_store import GoogleTokenStore
from qa_ba.api_tests.auth_helpers import user_headers


def configure_google_env(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_GMAIL_REDIRECT_URI", "http://127.0.0.1:8000/api/integrations/google/gmail/callback")
    monkeypatch.setenv("GOOGLE_CALENDAR_REDIRECT_URI", "http://127.0.0.1:8000/api/integrations/google/calendar/callback")
    get_backend_settings.cache_clear()


def logged_in_user_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.get("/api/auth/me", headers=headers).json()["user"]["user_id"]


def test_integration_status_shows_not_connected_initially(monkeypatch) -> None:
    configure_google_env(monkeypatch)
    client = TestClient(app)
    headers = user_headers(client)
    user_id = logged_in_user_id(client, headers)
    GoogleTokenStore().delete_token(user_id, "gmail")
    GoogleTokenStore().delete_token(user_id, "calendar")

    response = client.get("/api/integrations/google/status", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["google_login_configured"] is True
    assert body["gmail_connected"] is False
    assert body["calendar_connected"] is False


def test_gmail_and_calendar_start_require_auth(monkeypatch) -> None:
    configure_google_env(monkeypatch)
    client = TestClient(app)

    assert client.get("/api/integrations/google/gmail/start", follow_redirects=False).status_code == 401
    assert client.get("/api/integrations/google/calendar/start", follow_redirects=False).status_code == 401


def test_gmail_start_builds_readonly_scope_only(monkeypatch) -> None:
    configure_google_env(monkeypatch)
    client = TestClient(app)

    response = client.get("/api/integrations/google/gmail/start", headers=user_headers(client), follow_redirects=False)

    assert response.status_code == 307
    params = parse_qs(urlparse(response.headers["location"]).query)
    assert params["scope"] == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert params["redirect_uri"] == ["http://127.0.0.1:8000/api/integrations/google/gmail/callback"]
    assert "https://www.googleapis.com/auth/gmail.modify" not in params["scope"][0]
    assert "https://www.googleapis.com/auth/gmail.send" not in params["scope"][0]
    assert params.get("state", [""])[0]


def test_gmail_start_url_returns_json_for_frontend(monkeypatch) -> None:
    configure_google_env(monkeypatch)
    client = TestClient(app)

    response = client.get("/api/integrations/google/gmail/start-url", headers=user_headers(client))

    assert response.status_code == 200
    parsed = urlparse(response.json()["url"])
    params = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert params["scope"] == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert params["redirect_uri"] == ["http://127.0.0.1:8000/api/integrations/google/gmail/callback"]


def test_calendar_start_builds_readonly_scope_only(monkeypatch) -> None:
    configure_google_env(monkeypatch)
    client = TestClient(app)

    response = client.get("/api/integrations/google/calendar/start", headers=user_headers(client), follow_redirects=False)

    assert response.status_code == 307
    params = parse_qs(urlparse(response.headers["location"]).query)
    assert params["scope"] == ["https://www.googleapis.com/auth/calendar.readonly"]
    assert params["redirect_uri"] == ["http://127.0.0.1:8000/api/integrations/google/calendar/callback"]
    assert "https://www.googleapis.com/auth/calendar.events" not in params["scope"][0]
    assert params.get("state", [""])[0]


def test_calendar_start_url_returns_json_for_frontend(monkeypatch) -> None:
    configure_google_env(monkeypatch)
    client = TestClient(app)

    response = client.get("/api/integrations/google/calendar/start-url", headers=user_headers(client))

    assert response.status_code == 200
    parsed = urlparse(response.json()["url"])
    params = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert params["scope"] == ["https://www.googleapis.com/auth/calendar.readonly"]
    assert params["redirect_uri"] == ["http://127.0.0.1:8000/api/integrations/google/calendar/callback"]


def test_disconnect_removes_token(monkeypatch) -> None:
    configure_google_env(monkeypatch)
    client = TestClient(app)
    headers = user_headers(client)
    user_id = logged_in_user_id(client, headers)
    GoogleTokenStore().save_token(
        user_id,
        "gmail",
        {"access_token": "fake", "expires_in": 3600, "scope": "https://www.googleapis.com/auth/gmail.readonly"},
        google_account_email="student@example.com",
    )

    response = client.post("/api/integrations/google/gmail/disconnect", headers=headers)

    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert GoogleTokenStore().is_connected(user_id, "gmail") is False


def test_gmail_sync_not_connected_without_mock() -> None:
    client = TestClient(app)
    user_id = f"not-connected-{uuid.uuid4()}"

    response = client.post("/api/google/gmail/sync", json={"user_id": user_id, "use_mock": False})

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False
    assert body["source_mode"] == "not_connected"
    assert "Gmail chưa được kết nối" in body["message"]


def test_mock_sync_still_works() -> None:
    client = TestClient(app)
    user_id = f"mock-{uuid.uuid4()}"

    response = client.post("/api/google/gmail/sync", json={"user_id": user_id, "use_mock": True, "scenario": "student_clean"})

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["source_mode"] == "mock"
    assert body["mode"] == "mock:student_clean"


def test_daily_briefing_reports_mock_source_mode() -> None:
    client = TestClient(app)
    user_id = f"briefing-{uuid.uuid4()}"
    client.post("/api/google/gmail/sync", json={"user_id": user_id, "use_mock": True, "scenario": "student_clean"})
    client.post("/api/google/calendar/sync", json={"user_id": user_id, "use_mock": True, "scenario": "student_clean"})

    response = client.get(f"/api/assistant/daily-briefing?user_id={user_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["source_mode"] == "mock"
    assert body["metadata"]["gmail_connected"] is False
    assert body["metadata"]["calendar_connected"] is False

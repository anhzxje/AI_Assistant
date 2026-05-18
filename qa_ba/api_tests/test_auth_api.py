"""Tests for local auth and role enforcement."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from qa_ba.api_tests.auth_helpers import admin_headers, user_headers


def test_login_and_me_admin() -> None:
    client = TestClient(app)
    headers = admin_headers(client)

    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["role"] == "admin"
    assert body["user"]["role_label"] == "Người quản lý"


def test_admin_endpoint_rejects_user_role() -> None:
    client = TestClient(app)

    response = client.get("/api/admin/system-summary", headers=user_headers(client))

    assert response.status_code == 403
    assert "Người quản lý" in response.json()["detail"]


def test_admin_endpoint_requires_token() -> None:
    client = TestClient(app)

    response = client.get("/api/admin/system-summary")

    assert response.status_code == 401

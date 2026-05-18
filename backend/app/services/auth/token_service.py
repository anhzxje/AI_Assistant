"""Small signed-token service for local/demo authentication."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
from typing import Any

from backend.app.config import get_backend_settings


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


class TokenService:
    def __init__(self, secret_path: Path | None = None) -> None:
        settings = get_backend_settings()
        auth_root = settings.data_settings.resolved_data_root / "personal_memory" / "auth"
        self.secret_path = secret_path or auth_root / "token_secret.txt"
        self.ttl_seconds = settings.auth_token_ttl_seconds
        self.secret = self._load_secret()

    def create_token(self, payload: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        body = {
            **payload,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.ttl_seconds)).timestamp()),
            "jti": secrets.token_urlsafe(16),
        }
        header = {"alg": "HS256", "typ": "JWT"}
        header_part = _b64_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        body_part = _b64_encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signature = self._sign(f"{header_part}.{body_part}")
        return f"{header_part}.{body_part}.{signature}"

    def verify_token(self, token: str) -> dict[str, Any] | None:
        try:
            header_part, body_part, signature = token.split(".", 2)
            expected = self._sign(f"{header_part}.{body_part}")
            if not hmac.compare_digest(signature, expected):
                return None
            payload = json.loads(_b64_decode(body_part).decode("utf-8"))
            if int(payload.get("exp") or 0) < int(datetime.now(timezone.utc).timestamp()):
                return None
            return payload
        except Exception:
            return None

    def _sign(self, value: str) -> str:
        digest = hmac.new(self.secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).digest()
        return _b64_encode(digest)

    def _load_secret(self) -> str:
        env_secret = os.getenv("OMNI_AUTH_SECRET")
        if env_secret:
            return env_secret
        self.secret_path.parent.mkdir(parents=True, exist_ok=True)
        if self.secret_path.exists():
            return self.secret_path.read_text(encoding="utf-8").strip()
        secret = secrets.token_urlsafe(48)
        self.secret_path.write_text(secret, encoding="utf-8")
        return secret

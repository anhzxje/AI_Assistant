"""Allowlisted REST API ingestion connector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from data_platform.config import get_settings
from data_platform.governance.hashing import sha256_bytes


@dataclass(frozen=True)
class ApiIngestionResult:
    url: str
    raw_path: Path
    content_hash: str
    bytes_written: int


class ApiConnector:
    """Fetch JSON from an allowlisted endpoint into immutable raw storage."""

    def __init__(self, *, allowed_domains: tuple[str, ...] | None = None) -> None:
        settings = get_settings()
        self.allowed_domains = allowed_domains or settings.allowed_domains
        self.raw_root = settings.resolved_data_root / "raw" / "api"

    def fetch_json(self, url: str, *, headers: dict[str, str] | None = None) -> ApiIngestionResult:
        self._assert_allowed(url)
        request = Request(url, headers={"Accept": "application/json", **(headers or {})})
        with urlopen(request, timeout=20) as response:  # noqa: S310 - URL is allowlist checked above.
            payload = response.read()
        parsed = json.loads(payload.decode("utf-8"))
        normalized = json.dumps(parsed, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        digest = sha256_bytes(normalized)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_dir = self.raw_root / day
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{digest[:16]}.json"
        if not output_path.exists():
            output_path.write_bytes(normalized)
        return ApiIngestionResult(url=url, raw_path=output_path, content_hash=digest, bytes_written=len(normalized))

    def _assert_allowed(self, url: str) -> None:
        host = (urlparse(url).hostname or "").lower()
        if not host or not any(host == domain or host.endswith(f".{domain}") for domain in self.allowed_domains):
            raise ValueError(f"API ingestion blocked for non-allowlisted host: {host or url}")

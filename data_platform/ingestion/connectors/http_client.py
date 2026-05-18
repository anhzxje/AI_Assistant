"""HTTP client wrapper with retry, timeout, and crawler defaults."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status_code: int
    headers: dict[str, str]
    content: bytes

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "")


class HttpClient:
    """Small sync HTTP client for deterministic ingestion jobs."""

    def __init__(
        self,
        *,
        user_agent: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        self.max_retries = max_retries
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
                "Accept-Language": "vi,en;q=0.8",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def get(self, url: str) -> HttpResponse:
        return self._get_with_retry(url)

    def _get_with_retry(self, url: str) -> HttpResponse:
        @retry(
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)
            ),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            stop=stop_after_attempt(self.max_retries),
            reraise=True,
        )
        def _request() -> HttpResponse:
            response = self._client.get(url)
            if response.status_code in {429, 500, 502, 503, 504}:
                response.raise_for_status()
            return HttpResponse(
                url=str(response.url),
                status_code=response.status_code,
                headers={key.lower(): value for key, value in response.headers.items()},
                content=response.content,
            )

        return _request()

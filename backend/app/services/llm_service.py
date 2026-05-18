"""Local LLM integration through Ollama."""

from __future__ import annotations

import httpx

from backend.app.config import get_backend_settings


class OllamaService:
    _last_available: bool = False

    def __init__(self) -> None:
        settings = get_backend_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout_sec = settings.omni_llm_timeout_sec
        self.fast_mode = settings.omni_llm_fast_mode
        self.last_latency_ms: int | None = None
        self.last_error: str | None = None

    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            ok = response.status_code == 200
            if ok:
                OllamaService._last_available = True
            return ok
        except Exception:
            return OllamaService._last_available

    def generate(self, prompt: str, *, temperature: float = 0.1, num_ctx: int = 4096) -> str | None:
        import time

        started = time.perf_counter()
        self.last_error = None
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_ctx": min(num_ctx, 3072) if self.fast_mode else num_ctx,
                        "num_predict": 320 if self.fast_mode else 768,
                        "top_p": 0.9,
                    },
                },
                timeout=self.timeout_sec,
            )
            self.last_latency_ms = int((time.perf_counter() - started) * 1000)
            if response.status_code != 200:
                self.last_error = f"ollama_generate_http_{response.status_code}"
                return None
            data = response.json()
            content = str(data.get("response") or "").strip() or None
            if content:
                OllamaService._last_available = True
            return content
        except Exception as exc:
            self.last_latency_ms = int((time.perf_counter() - started) * 1000)
            self.last_error = str(exc)
            return None

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.1, num_ctx: int = 4096) -> str | None:
        import time

        started = time.perf_counter()
        self.last_error = None
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_ctx": min(num_ctx, 3072) if self.fast_mode else num_ctx,
                        "num_predict": 320 if self.fast_mode else 768,
                        "top_p": 0.9,
                    },
                },
                timeout=self.timeout_sec,
            )
            self.last_latency_ms = int((time.perf_counter() - started) * 1000)
            if response.status_code != 200:
                self.last_error = f"ollama_chat_http_{response.status_code}"
                return None
            data = response.json()
            message = data.get("message") or {}
            content = str(message.get("content") or "").strip() or None
            if content:
                OllamaService._last_available = True
            return content
        except Exception as exc:
            self.last_latency_ms = int((time.perf_counter() - started) * 1000)
            self.last_error = str(exc)
            return None

    def warmup(self) -> bool:
        ok = self.generate("OK", temperature=0.0, num_ctx=256) is not None
        if ok:
            OllamaService._last_available = True
        return ok


def llm_status() -> str:
    return "ollama" if OllamaService().is_available() else "fallback"

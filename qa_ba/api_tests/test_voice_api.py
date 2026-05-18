"""FastAPI tests for optional voice layer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ai_module.asr.faster_whisper_service import ASRUnavailableError
from backend.app.main import app


def test_voice_transcribe_missing_file() -> None:
    client = TestClient(app)
    response = client.post("/api/voice/transcribe")

    assert response.status_code == 422


def test_voice_speak_text_fallback() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/voice/speak",
        json={"text": "Xin chào, đây là kiểm thử giọng nói.", "voice": "default", "language": "vi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["audio_url"].startswith("/api/voice/audio/")
    assert body["format"] in {"mp3", "wav"}
    assert body["latency_ms"] >= 0


def test_voice_chat_missing_file() -> None:
    client = TestClient(app)
    response = client.post("/api/voice/chat", data={"user_id": "default"})

    assert response.status_code == 422


def test_voice_transcribe_dependency_unavailable(monkeypatch) -> None:
    from backend.app.api import voice as voice_api

    class UnavailableASR:
        def transcribe(self, path, *, language: str = "vi"):
            raise ASRUnavailableError("ASR dependency unavailable for test")

    monkeypatch.setattr(voice_api, "get_asr_service", lambda: UnavailableASR())
    client = TestClient(app)
    response = client.post(
        "/api/voice/transcribe",
        files={"file": ("sample.wav", b"not-a-real-wav", "audio/wav")},
    )

    assert response.status_code == 503
    assert "ASR dependency unavailable" in response.json()["detail"]

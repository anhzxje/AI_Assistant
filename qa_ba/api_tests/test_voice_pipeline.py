from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.voice.voice_answer_policy import build_spoken_answer


def test_voice_speak_returns_audio_or_graceful_fallback() -> None:
    response = TestClient(app).post("/api/voice/speak", json={"text": "Xin chào", "language": "vi"})

    assert response.status_code == 200
    body = response.json()
    assert body["audio_url"]
    assert body["mode"] in {"edge-tts", "fallback_wav"}


def test_voice_chat_missing_file_returns_validation_error() -> None:
    response = TestClient(app).post("/api/voice/chat", data={"user_id": "test"})

    assert response.status_code == 422


def test_spoken_answer_shorter_than_long_answer() -> None:
    answer = "\n".join(
        [
            "- Sinh viên học khoa học máy tính [1].",
            "- Sinh viên học thống kê [1].",
            "- Sinh viên học toán ứng dụng [1].",
            "- Sinh viên học lập trình [1].",
            "- Sinh viên học phân tích dữ liệu [1].",
        ]
    )

    spoken = build_spoken_answer(answer, intent="institutional_rag", has_sources=True)

    assert len(spoken) < len(answer)
    assert "[1]" not in spoken
    assert "Theo dữ liệu" in spoken


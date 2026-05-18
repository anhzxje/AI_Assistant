"""Local/free TTS service with edge-tts preference and safe fallback."""

from __future__ import annotations

import asyncio
import importlib.util
import math
import time
import uuid
import wave
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from backend.app.config import get_backend_settings


@dataclass(frozen=True)
class TTSResult:
    audio_url: str
    format: str
    latency_ms: int
    mode: str
    text_url: str | None = None


class TTSService:
    def __init__(self) -> None:
        settings = get_backend_settings()
        self.data_root = settings.data_settings.resolved_data_root
        self.provider = settings.tts_provider
        self.voice = settings.tts_voice
        self.rate = settings.tts_rate
        self.pitch = settings.tts_pitch

    def mode(self) -> str:
        return "edge-tts" if self.provider == "edge" and importlib.util.find_spec("edge_tts") else "fallback_wav"

    def synthesize(self, *, text: str, voice: str = "default", language: str = "vi") -> TTSResult:
        started = time.perf_counter()
        output_dir = self._output_dir()
        stem = uuid.uuid4().hex
        if self.provider == "edge" and importlib.util.find_spec("edge_tts"):
            audio_path = output_dir / f"{stem}.mp3"
            asyncio.run(self._edge_tts(text=text, voice=voice_name(voice, language), audio_path=audio_path))
            return TTSResult(
                audio_url=audio_url(audio_path),
                format="mp3",
                latency_ms=int((time.perf_counter() - started) * 1000),
                mode="edge-tts",
            )

        text_path = output_dir / f"{stem}.txt"
        wav_path = output_dir / f"{stem}.wav"
        text_path.write_text(text, encoding="utf-8")
        write_placeholder_wav(wav_path, duration_sec=min(2.0, max(0.4, len(text) / 120.0)))
        return TTSResult(
            audio_url=audio_url(wav_path),
            format="wav",
            latency_ms=int((time.perf_counter() - started) * 1000),
            mode="fallback_wav",
            text_url=audio_url(text_path),
        )

    async def _edge_tts(self, *, text: str, voice: str, audio_path: Path) -> None:
        import edge_tts

        communicate = edge_tts.Communicate(text, voice, rate=self.rate, pitch=self.pitch)
        await communicate.save(str(audio_path))

    def _output_dir(self) -> Path:
        output = self.data_root / "generated" / "audio" / date.today().isoformat()
        output.mkdir(parents=True, exist_ok=True)
        return output


def voice_name(voice: str, language: str) -> str:
    if voice != "default":
        return voice
    configured = get_backend_settings().tts_voice
    if configured:
        return configured
    if language == "vi":
        return "vi-VN-HoaiMyNeural"
    return "en-US-JennyNeural"


def write_placeholder_wav(path: Path, *, duration_sec: float) -> None:
    sample_rate = 16000
    frames = int(sample_rate * duration_sec)
    amplitude = 0
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for _ in range(frames):
            handle.writeframesraw(int(amplitude * math.sin(0)).to_bytes(2, "little", signed=True))


def audio_url(path: Path) -> str:
    date_part = path.parent.name
    return f"/api/voice/audio/{date_part}/{path.name}"

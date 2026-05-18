"""faster-whisper ASR wrapper with lazy model loading."""

from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.config import get_backend_settings


class ASRUnavailableError(RuntimeError):
    """Raised when ASR dependencies or model runtime are unavailable."""


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    duration_sec: float
    model: str
    latency_ms: int
    segments: list[dict[str, Any]]
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    confidence: float | None = None


class FasterWhisperService:
    def __init__(self) -> None:
        settings = get_backend_settings()
        self.model_size = settings.whisper_model_size
        self.device = resolve_device(settings.whisper_device)
        self.compute_type = resolve_compute_type(settings.whisper_compute_type, self.device)
        self.language = settings.whisper_language
        self.beam_size = settings.whisper_beam_size
        self.vad_filter = settings.whisper_vad_filter
        self.no_speech_threshold = settings.whisper_no_speech_threshold
        self.log_prob_threshold = settings.whisper_log_prob_threshold
        self.compression_ratio_threshold = settings.whisper_compression_ratio_threshold
        self._model = None

    def available(self) -> bool:
        return importlib.util.find_spec("faster_whisper") is not None

    def transcribe(self, path: Path, *, language: str | None = None) -> TranscriptionResult:
        if not self.available():
            raise ASRUnavailableError(
                "faster-whisper is not installed. Install `.[voice]` or `python -m pip install faster-whisper`."
            )
        started = time.perf_counter()
        model = self._load_model()
        resolved_language = language or self.language
        segments_iter, info = model.transcribe(
            str(path),
            language=resolved_language,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
            no_speech_threshold=self.no_speech_threshold,
            log_prob_threshold=self.log_prob_threshold,
            compression_ratio_threshold=self.compression_ratio_threshold,
        )
        segment_rows = []
        for segment in segments_iter:
            text = segment.text.strip()
            if not text:
                continue
            segment_rows.append(
                {
                    "start": round(float(segment.start), 3),
                    "end": round(float(segment.end), 3),
                    "text": text,
                    "avg_logprob": getattr(segment, "avg_logprob", None),
                    "no_speech_prob": getattr(segment, "no_speech_prob", None),
                }
            )
        text = " ".join(segment["text"] for segment in segment_rows).strip()
        avg_logprob = average_optional([segment.get("avg_logprob") for segment in segment_rows])
        no_speech_prob = average_optional([segment.get("no_speech_prob") for segment in segment_rows])
        latency_ms = int((time.perf_counter() - started) * 1000)
        return TranscriptionResult(
            text=text,
            language=getattr(info, "language", None) or resolved_language,
            duration_sec=round(float(getattr(info, "duration", 0.0) or 0.0), 3),
            model=self.model_size,
            latency_ms=latency_ms,
            segments=segment_rows,
            avg_logprob=avg_logprob,
            no_speech_prob=no_speech_prob,
            confidence=estimate_confidence(avg_logprob=avg_logprob, no_speech_prob=no_speech_prob, text=text),
        )

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            return self._model
        except Exception as exc:  # noqa: BLE001 - model download/runtime failures should be clear.
            raise ASRUnavailableError(f"faster-whisper model is unavailable: {exc}") from exc


def resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def resolve_compute_type(configured: str, device: str) -> str:
    if configured != "auto":
        return configured
    return "int8_float16" if device == "cuda" else "int8"


def average_optional(values: list[Any]) -> float | None:
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 4)


def estimate_confidence(*, avg_logprob: float | None, no_speech_prob: float | None, text: str) -> float:
    if not text:
        return 0.0
    score = 0.75
    if avg_logprob is not None:
        score += max(-0.25, min(0.2, (avg_logprob + 0.5) * 0.25))
    if no_speech_prob is not None:
        score -= max(0.0, min(0.45, no_speech_prob * 0.45))
    return round(max(0.0, min(1.0, score)), 3)

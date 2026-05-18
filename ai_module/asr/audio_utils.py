"""Audio file helpers for ASR endpoints."""

from __future__ import annotations

import shutil
import subprocess
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from backend.app.config import get_backend_settings


@dataclass(frozen=True)
class SavedAudio:
    path: Path
    filename: str
    content_type: str | None
    duration_sec: float
    processed_path: Path | None = None


def save_upload_file(upload: UploadFile) -> SavedAudio:
    suffix = Path(upload.filename or "audio.webm").suffix or ".webm"
    filename = f"{uuid.uuid4().hex}{suffix.lower()}"
    target_dir = get_backend_settings().data_settings.resolved_data_root / "raw" / "voice"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    with target.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)
    processed = preprocess_for_asr(target)
    return SavedAudio(
        path=target,
        filename=filename,
        content_type=upload.content_type,
        duration_sec=estimate_duration_sec(processed or target),
        processed_path=processed,
    )


def estimate_duration_sec(path: Path) -> float:
    if path.suffix.lower() != ".wav":
        return 0.0
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            return round(frames / float(rate), 3) if rate else 0.0
    except Exception:
        return 0.0


def preprocess_for_asr(path: Path) -> Path | None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    output_dir = get_backend_settings().data_settings.resolved_data_root / "processed" / "voice"
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{path.stem}_16k.wav"
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-af",
        "silenceremove=start_periods=1:start_duration=0.15:start_threshold=-45dB:stop_periods=1:stop_duration=0.35:stop_threshold=-45dB,dynaudnorm=f=150:g=15",
        str(target),
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        return target if target.exists() else None
    except Exception:
        return None

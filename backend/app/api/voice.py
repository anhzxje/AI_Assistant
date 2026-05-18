"""Voice API endpoints for push-to-talk assistant interaction."""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ai_module.asr.audio_utils import save_upload_file
from ai_module.asr.faster_whisper_service import ASRUnavailableError, FasterWhisperService
from ai_module.tts.tts_service import TTSService
from backend.app.config import get_backend_settings
from backend.app.schemas.voice_schema import (
    SpeakRequest,
    SpeakResponse,
    TranscribeResponse,
    VoiceChatResponse,
)
from backend.app.services.auth.auth_service import get_current_user_optional
from backend.app.services.auth.user_store import UserRecord
from backend.app.services.voice.voice_answer_policy import build_spoken_answer
from orchestration.assistant_graph import AssistantGraph

router = APIRouter(tags=["voice"])


@router.post("/api/voice/transcribe", response_model=TranscribeResponse)
def transcribe_audio(file: UploadFile = File(...)) -> TranscribeResponse:
    saved = save_upload_file(file)
    try:
        result = get_asr_service().transcribe(saved.path, language="vi")
    except ASRUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return TranscribeResponse(
        text=result.text,
        language=result.language,
        duration_sec=result.duration_sec or saved.duration_sec,
        model=result.model,
        latency_ms=result.latency_ms,
        segments=result.segments,
        avg_logprob=result.avg_logprob,
        no_speech_prob=result.no_speech_prob,
        confidence=result.confidence,
    )


@router.post("/api/voice/speak", response_model=SpeakResponse)
def speak(request: SpeakRequest) -> SpeakResponse:
    result = get_tts_service().synthesize(
        text=request.text,
        voice=request.voice,
        language=request.language,
    )
    return SpeakResponse(**result.__dict__)


@router.post("/api/voice/chat", response_model=VoiceChatResponse)
def voice_chat(
    file: UploadFile = File(...),
    user_id: str = Form(default="default"),
    session_id: str | None = Form(default=None),
    include_memory: bool = Form(default=True),
    use_mock_google: bool = Form(default=True),
    voice_mode: str = Form(default="push_to_talk"),
    user: UserRecord | None = Depends(get_current_user_optional),
) -> VoiceChatResponse:
    started = time.perf_counter()
    saved = save_upload_file(file)
    try:
        transcription = get_asr_service().transcribe(saved.processed_path or saved.path, language=get_backend_settings().whisper_language)
    except ASRUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not transcription.text.strip():
        raise HTTPException(status_code=422, detail="Mình chưa nghe rõ, bạn thử nói lại nhé.")

    resolved_user_id = user.user_id if user is not None else user_id
    assistant_started = time.perf_counter()
    assistant_state = get_assistant_graph().invoke(
        user_id=resolved_user_id,
        session_id=session_id,
        message=transcription.text,
        include_memory=include_memory,
        use_mock_google=use_mock_google,
        auth_role=user.role if user is not None else "user",
    )
    assistant_latency_ms = int((time.perf_counter() - assistant_started) * 1000)
    spoken_answer = build_spoken_answer(
        assistant_state["answer"],
        intent=assistant_state["intent"],
        has_sources=bool(assistant_state.get("sources")),
    )
    tts = get_tts_service().synthesize(text=spoken_answer, language="vi")
    total_latency_ms = int((time.perf_counter() - started) * 1000)
    metadata = {
        **assistant_state["metadata"],
        "voice_latency_ms": total_latency_ms,
        "latency_ms": total_latency_ms,
        "asr_latency_ms": transcription.latency_ms,
        "assistant_latency_ms": assistant_latency_ms,
        "tts_latency_ms": tts.latency_ms,
        "audio_duration_sec": transcription.duration_sec or saved.duration_sec,
        "transcript_confidence": transcription.confidence,
        "voice_mode": voice_mode,
        "asr": {
            "model": transcription.model,
            "language": transcription.language,
            "duration_sec": transcription.duration_sec or saved.duration_sec,
            "latency_ms": transcription.latency_ms,
            "segments": transcription.segments,
            "avg_logprob": transcription.avg_logprob,
            "no_speech_prob": transcription.no_speech_prob,
            "confidence": transcription.confidence,
        },
        "tts": {
            "mode": tts.mode,
            "format": tts.format,
            "latency_ms": tts.latency_ms,
            "text_url": tts.text_url,
        },
    }
    return VoiceChatResponse(
        transcript=transcription.text,
        answer=assistant_state["answer"],
        spoken_answer=spoken_answer,
        intent=assistant_state["intent"],
        sources=assistant_state.get("sources", []),
        actions=assistant_state.get("actions", ["voice_chat"]),
        memory_used=bool(assistant_state.get("memory_used")),
        audio_url=tts.audio_url,
        metadata=metadata,
    )


@router.get("/api/voice/audio/{date_dir}/{filename}")
def get_generated_audio(date_dir: str, filename: str) -> FileResponse:
    root = get_backend_settings().data_settings.resolved_data_root / "generated" / "audio"
    target = (root / date_dir / filename).resolve()
    if root.resolve() not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid audio path")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(target)


@lru_cache(maxsize=1)
def get_asr_service() -> FasterWhisperService:
    return FasterWhisperService()


@lru_cache(maxsize=1)
def get_tts_service() -> TTSService:
    return TTSService()


@lru_cache(maxsize=1)
def get_assistant_graph() -> AssistantGraph:
    return AssistantGraph()

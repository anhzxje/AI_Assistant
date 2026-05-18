"""Schemas for voice APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration_sec: float
    model: str
    latency_ms: int
    segments: list[dict[str, Any]] = Field(default_factory=list)
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    confidence: float | None = None


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1)
    voice: str = "default"
    language: str = "vi"


class SpeakResponse(BaseModel):
    audio_url: str
    format: str
    latency_ms: int
    mode: str
    text_url: str | None = None


class VoiceChatResponse(BaseModel):
    transcript: str
    answer: str
    spoken_answer: str
    intent: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    memory_used: bool = False
    audio_url: str
    metadata: dict[str, Any]

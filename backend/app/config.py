"""Backend runtime settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from data_platform.config import get_settings


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b-instruct"
    omni_force_llm: bool = True
    omni_llm_timeout_sec: float = 20.0
    omni_llm_fast_mode: bool = True
    omni_llm_warmup_on_startup: bool = True

    omni_query_embedding_cache_ttl_sec: int = 3600
    omni_retrieval_cache_ttl_sec: int = 900
    omni_answer_cache_ttl_sec: int = 900

    default_top_k: int = 5
    postgres_dsn: str = "postgresql://omni:omni@localhost:5432/omni_assistant"
    redis_url: str = "redis://localhost:6379/0"
    memory_session_ttl_seconds: int = 86400
    memory_session_max_turns: int = 12
    semantic_memory_collection: str = "omni_user_memory"
    google_client_secret_path: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://127.0.0.1:8000/api/auth/google/callback"
    google_gmail_redirect_uri: str = "http://127.0.0.1:8000/api/integrations/google/gmail/callback"
    google_calendar_redirect_uri: str = "http://127.0.0.1:8000/api/integrations/google/calendar/callback"
    frontend_url: str = "http://127.0.0.1:3002"
    whisper_model_size: str = "small"
    whisper_device: str = "auto"
    whisper_compute_type: str = "int8"
    whisper_language: str = "vi"
    whisper_beam_size: int = 5
    whisper_vad_filter: bool = True
    whisper_no_speech_threshold: float = 0.6
    whisper_log_prob_threshold: float = -1.0
    whisper_compression_ratio_threshold: float = 2.4
    omni_voice_fast_mode: bool = True
    tts_provider: str = "edge"
    tts_voice: str = "vi-VN-HoaiMyNeural"
    tts_rate: str = "+0%"
    tts_pitch: str = "+0Hz"
    auth_token_ttl_seconds: int = 60 * 60 * 12

    @property
    def data_settings(self):
        return get_settings()


@lru_cache(maxsize=1)
def get_backend_settings() -> BackendSettings:
    return BackendSettings()

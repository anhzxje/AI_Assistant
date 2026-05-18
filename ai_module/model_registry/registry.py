"""Local model registry for the assistant/RAG stack."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from backend.app.config import get_backend_settings
from data_platform.config import get_settings


def registry_path() -> Path:
    return get_settings().metadata_root / "model_registry.json"


def build_registry(eval_metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_settings = get_backend_settings()
    data_settings = get_settings()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": {
            "embedding": {
                "name": data_settings.embedding_model_name,
                "fallback": data_settings.embedding_fallback_model_name,
                "serving": "singleton sentence-transformers adapter",
            },
            "llm": {
                "provider": "ollama",
                "name": backend_settings.ollama_model,
                "base_url": backend_settings.ollama_base_url,
            },
            "asr": {
                "provider": "faster-whisper",
                "configured_model": backend_settings.whisper_model_size,
                "language": backend_settings.whisper_language,
            },
            "tts": {
                "provider": backend_settings.tts_provider,
                "voice": backend_settings.tts_voice,
            },
            "vector_store": {
                "provider": "qdrant",
                "collection": data_settings.qdrant_collection,
            },
        },
        "metrics": eval_metrics or load_eval_metrics(),
        "management": {
            "registry_type": "local_json",
            "mlflow_status": "deferred_mvp",
            "notes": "Heavy LLM fine-tuning is out of scope; retrieval, prompts, intent routing, ASR, and TTS are evaluated locally.",
        },
    }


def write_registry(eval_metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = build_registry(eval_metrics)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def load_registry() -> dict[str, Any]:
    path = registry_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return write_registry()


def load_eval_metrics() -> dict[str, Any]:
    reports = Path("qa_ba/reports")
    metrics: dict[str, Any] = {}
    for name in ["retrieval_eval_report.json", "rag_eval_report.json", "feedback_eval_report.json", "latency_benchmark_after_hot.json"]:
        path = reports / name
        if path.exists():
            metrics[name] = json.loads(path.read_text(encoding="utf-8"))
    return metrics

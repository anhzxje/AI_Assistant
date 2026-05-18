"""FastAPI entrypoint for OmniAssistant backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread

from backend.app.api.action_studio import router as action_studio_router
from backend.app.api.admin import router as admin_router
from backend.app.api.assistant import router as assistant_router
from backend.app.api.auth import router as auth_router
from backend.app.api.briefing import router as briefing_router
from backend.app.api.feedback import router as feedback_router
from backend.app.api.google import router as google_router
from backend.app.api.health import router as health_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.knowledge import router as knowledge_router
from backend.app.api.memory import router as memory_router
from backend.app.api.predict import router as predict_router
from backend.app.api.rag import router as rag_router
from backend.app.api.voice import router as voice_router
from backend.app.config import get_backend_settings
from backend.app.services.llm_service import OllamaService
from backend.app.services.retriever_service import get_retriever_service

app = FastAPI(title="Lumi Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3010",
        "http://127.0.0.1:3010",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Location"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(rag_router)
app.include_router(admin_router)
app.include_router(memory_router)
app.include_router(google_router)
app.include_router(briefing_router)
app.include_router(knowledge_router)
app.include_router(assistant_router)
app.include_router(predict_router)
app.include_router(voice_router)
app.include_router(feedback_router)
app.include_router(jobs_router)
app.include_router(action_studio_router)


@app.on_event("startup")
def warmup_local_llm() -> None:
    if not get_backend_settings().omni_llm_warmup_on_startup:
        return

    def _warmup() -> None:
        OllamaService().warmup()
        try:
            _ = get_retriever_service().embedding_model.info
        except Exception:
            pass

    Thread(target=_warmup, daemon=True).start()

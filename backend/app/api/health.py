"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.services.llm_service import llm_status
from backend.app.services.retriever_service import qdrant_status

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "qdrant": qdrant_status(),
        "llm": llm_status(),
    }

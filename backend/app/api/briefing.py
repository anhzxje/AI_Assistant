"""Smart briefing and context APIs."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends

from backend.app.services.auth.auth_service import get_current_user
from backend.app.services.auth.user_store import UserRecord
from backend.app.services.briefing.briefing_schema import SmartBriefing
from backend.app.services.briefing.smart_briefing import SmartBriefingService
from backend.app.services.connectors.personal_ingestion import PersonalIngestionService
from backend.app.services.context.context_engine import ContextEngine
from backend.app.services.context.context_schema import PersonalContext
from backend.app.services.integrations.google_token_store import GoogleTokenStore

router = APIRouter(tags=["briefing"])


@router.post("/api/briefing/generate", response_model=SmartBriefing)
def generate_smart_briefing(
    time_window: str = "today",
    allow_mock: bool = False,
    user: UserRecord = Depends(get_current_user),
) -> SmartBriefing:
    if not allow_mock:
        clear_disconnected_sources(user.user_id)
    return get_smart_briefing_service().generate(user_id=user.user_id, time_window=time_window)


@router.get("/api/briefing/latest", response_model=SmartBriefing)
def latest_smart_briefing(user: UserRecord = Depends(get_current_user)) -> SmartBriefing:
    return get_smart_briefing_service().latest(user_id=user.user_id)


@router.get("/api/context/latest", response_model=PersonalContext)
def latest_context(user: UserRecord = Depends(get_current_user)) -> PersonalContext:
    return get_context_engine().latest(user_id=user.user_id) or get_context_engine().build(user_id=user.user_id)


@router.post("/api/context/generate", response_model=PersonalContext)
def generate_context(time_window: str = "today", user: UserRecord = Depends(get_current_user)) -> PersonalContext:
    return get_context_engine().build(user_id=user.user_id, time_window=time_window)


@lru_cache(maxsize=1)
def get_smart_briefing_service() -> SmartBriefingService:
    return SmartBriefingService()


@lru_cache(maxsize=1)
def get_context_engine() -> ContextEngine:
    return ContextEngine()


def clear_disconnected_sources(user_id: str) -> None:
    tokens = GoogleTokenStore()
    ingestion = PersonalIngestionService()
    if not tokens.is_connected(user_id, "gmail"):
        ingestion.clear_gmail_for_user(user_id=user_id)
    if not tokens.is_connected(user_id, "calendar"):
        ingestion.clear_calendar_for_user(user_id=user_id)

"""Assistant orchestration API."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends

from backend.app.schemas.assistant_schema import AssistantChatRequest, AssistantChatResponse
from backend.app.services.auth.auth_service import get_current_user_optional
from backend.app.services.auth.user_store import UserRecord
from orchestration.assistant_graph import AssistantGraph

router = APIRouter(tags=["assistant"])


@router.post("/api/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(
    request: AssistantChatRequest,
    user: UserRecord | None = Depends(get_current_user_optional),
) -> AssistantChatResponse:
    user_id = user.user_id if user is not None else request.user_id
    state = get_assistant_graph().invoke(
        user_id=user_id,
        session_id=request.session_id,
        message=request.message,
        include_memory=request.include_memory,
        use_mock_google=request.use_mock_google,
        auth_role=user.role if user is not None else "user",
    )
    return AssistantChatResponse(
        answer=state["answer"],
        intent=state["intent"],
        sources=state["sources"],
        actions=state["actions"],
        memory_used=state["memory_used"],
        metadata=state["metadata"],
    )


@lru_cache(maxsize=1)
def get_assistant_graph() -> AssistantGraph:
    return AssistantGraph()

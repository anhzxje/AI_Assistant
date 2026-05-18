"""RAG API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.schemas.rag_schema import RagQueryRequest, RagQueryResponse
from backend.app.services.auth.auth_service import get_current_user_optional
from backend.app.services.auth.user_store import UserRecord
from backend.app.services.answer_service import AnswerService
from backend.app.services.llm_service import OllamaService
from backend.app.api.memory import get_memory_context_service
from backend.app.services.retriever_service import get_retriever_service

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/query", response_model=RagQueryResponse)
def query_rag(
    request: RagQueryRequest,
    user: UserRecord | None = Depends(get_current_user_optional),
) -> RagQueryResponse:
    resolved_user_id = user.user_id if user is not None else request.user_id
    service = AnswerService(
        retriever_service=get_retriever_service(),
        llm_service=OllamaService(),
        memory_service=get_memory_context_service(),
    )
    return service.answer(
        query=request.query,
        top_k=request.top_k,
        use_llm=request.use_llm,
        user_id=resolved_user_id,
        session_id=request.session_id,
        include_memory=request.include_memory,
    )

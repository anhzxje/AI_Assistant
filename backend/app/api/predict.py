"""Compatibility prediction endpoint for rubric/model-serving checks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ai_module.serving.api import predict as serve_prediction
from backend.app.services.auth.auth_service import get_current_user_optional
from backend.app.services.auth.user_store import UserRecord

router = APIRouter(tags=["predict"])


class PredictRequest(BaseModel):
    query: str = Field(min_length=1)
    user_id: str = "default"
    session_id: str | None = None
    include_memory: bool = True
    use_mock_google: bool = True


class PredictResponse(BaseModel):
    prediction: str
    intent: str | None
    confidence: float
    metadata: dict[str, Any]
    sources: list[dict[str, Any]] = []
    actions: list[str] = []


@router.post("/api/predict", response_model=PredictResponse)
def predict(request: PredictRequest, user: UserRecord | None = Depends(get_current_user_optional)) -> PredictResponse:
    result = serve_prediction(
        request.query,
        user_id=user.user_id if user is not None else request.user_id,
        session_id=request.session_id,
        include_memory=request.include_memory,
        use_mock_google=request.use_mock_google,
        auth_role=user.role if user is not None else "user",
    )
    return PredictResponse(**result)

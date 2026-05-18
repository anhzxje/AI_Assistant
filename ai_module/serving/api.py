"""Serving adapter used by the compatibility /api/predict endpoint."""

from __future__ import annotations

from typing import Any

from ai_module.models.rag_model import RagAssistantModel


def predict(query: str, **kwargs: Any) -> dict[str, Any]:
    prediction = RagAssistantModel().predict(query, **kwargs)
    state = prediction.metadata
    return {
        "prediction": prediction.text,
        "intent": state.get("intent"),
        "confidence": prediction.confidence,
        "metadata": state.get("metadata", {}),
        "sources": state.get("sources", []),
        "actions": state.get("actions", []),
    }

"""Institutional RAG node."""

from __future__ import annotations

from backend.app.services.answer_service import AnswerService
from backend.app.services.llm_service import OllamaService
from backend.app.services.retriever_service import get_retriever_service
from backend.app.api.memory import get_memory_context_service


def run(state: dict) -> dict:
    try:
        response = AnswerService(
            retriever_service=get_retriever_service(),
            llm_service=OllamaService(),
            memory_service=get_memory_context_service(),
        ).answer(
            query=state.get("retrieval_query") or state["message"],
            top_k=state.get("top_k", 5),
            use_llm=state.get("use_llm", True),
            user_id=state["user_id"],
            session_id=state.get("session_id"),
            include_memory=state.get("include_memory", True),
        )
        state["answer"] = response.answer
        state["sources"] = [citation.model_dump(mode="json") for citation in response.citations]
        state["actions"] = ["institutional_rag_retrieval"]
        state["memory_used"] = response.metadata.memory_items > 0
        state["metadata"]["rag"] = response.metadata.model_dump(mode="json")
        state["metadata"]["general_llm_mode"] = "ollama" if response.metadata.mode.startswith("ollama") else response.metadata.mode
        state["metadata"]["debug_retrieval"] = [
            citation.model_dump(mode="json") for citation in response.debug_retrieval
        ]
        state["metadata"]["original_query"] = state["message"]
    except Exception as exc:  # noqa: BLE001 - route should fail gracefully.
        state["answer"] = "Institutional retrieval is temporarily unavailable. Please try again after the vector store is ready."
        state["sources"] = []
        state["actions"] = ["institutional_rag_error"]
        state["metadata"]["error"] = str(exc)
    return state

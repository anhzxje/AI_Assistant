"""LangGraph-style assistant graph.

LangGraph can replace this runner later because the interface is deliberately
state-in/state-out with named nodes and route metadata.
"""

from __future__ import annotations

import time
from typing import Any

from backend.app.services.conversation.context_builder import ConversationContextBuilder
from backend.app.services.conversation.conversation_store import ConversationStore
from backend.app.services.llm_service import llm_status
from backend.app.services.quality.answer_diagnostics import diagnose_answer
from orchestration.intent_classifier_v2 import classify_intent_v2
from orchestration.nodes import (
    action_studio_node,
    briefing_node,
    calendar_node,
    clarification_node,
    date_time_node,
    fallback_node,
    general_chat_node,
    gmail_node,
    memory_node,
    rag_node,
    task_node,
)


NODE_BY_INTENT = {
    "institutional_rag": rag_node.run,
    "rag": rag_node.run,
    "personal_memory": memory_node.run,
    "memory": memory_node.run,
    "tasks": task_node.run,
    "gmail": gmail_node.run,
    "calendar": calendar_node.run,
    "daily_briefing": briefing_node.run,
    "action_studio": action_studio_node.run,
    "date_time": date_time_node.run,
    "general_chat": general_chat_node.run,
    "clarification": clarification_node.run,
    "fallback": fallback_node.run,
}


class AssistantGraph:
    def invoke(
        self,
        *,
        user_id: str,
        session_id: str | None,
        message: str,
        include_memory: bool = True,
        use_mock_google: bool = False,
        auth_role: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        resolved_session_id = session_id or "default"
        conversation_store = ConversationStore()
        conversation_context = ConversationContextBuilder(conversation_store).build(
            user_id=user_id,
            session_id=resolved_session_id,
            current_message=message,
        )
        classification = classify_intent_v2(message, conversation_context)
        node_name = classification.intent if classification.intent in NODE_BY_INTENT else "fallback"
        route = ["conversation_context", "intent_classifier_v2", route_node_label(node_name)]
        retrieval_query = classification.rewritten_query or message
        user_record = conversation_store.add_message(
            user_id=user_id,
            session_id=resolved_session_id,
            role="user",
            content=message,
            metadata={
                "intent": node_name,
                "classification": classification.to_metadata(),
                "topic_hint": retrieval_query if node_name in {"institutional_rag", "rag"} else None,
                "retrieval_query": retrieval_query if node_name in {"institutional_rag", "rag"} else None,
            },
        )
        state: dict[str, Any] = {
            "user_id": user_id,
            "session_id": resolved_session_id,
            "message": message,
            "retrieval_query": retrieval_query,
            "top_k": 6 if node_name in {"institutional_rag", "rag"} else 5,
            "use_llm": node_name in {"institutional_rag", "rag", "general_chat"},
            "include_memory": include_memory,
            "use_mock_google": use_mock_google,
            "auth_role": auth_role or "user",
            "intent": node_name,
            "conversation_context": conversation_context.to_metadata(),
            "answer": "",
            "sources": [],
            "actions": [],
            "memory_used": False,
            "metadata": {
                "route": route,
                "conversation_used": True,
                "session_id": resolved_session_id,
                "user_message_id": user_record.message_id,
                "intent_classifier": classification.to_metadata(),
                "conversation_context": {
                    "has_followup_reference": conversation_context.has_followup_reference,
                    "last_topic_hint": conversation_context.last_topic_hint,
                    "previous_intent": conversation_context.previous_intent,
                },
                "general_llm_mode": "not_used",
                "llm_status": llm_status(),
                "auth_role": auth_role or "user",
            },
        }
        state = NODE_BY_INTENT[node_name](state)
        latency_ms = int((time.perf_counter() - started) * 1000)
        state["metadata"]["latency_ms"] = latency_ms
        quality = diagnose_answer(
            query=message,
            answer=str(state.get("answer", "")),
            intent=str(state.get("intent", node_name)),
            sources=state.get("sources", []),
            metadata=state.get("metadata", {}),
            latency_ms=latency_ms,
        )
        state["metadata"]["quality"] = {
            "quality_score": quality["quality_score"],
            "issues": quality["issues"],
            "suggested_feedback_reason": quality["suggested_feedback_reason"],
            "requires_admin_review": quality["requires_admin_review"],
        }
        state["metadata"]["feedback_diagnostics"] = quality["diagnostics"]
        assistant_record = conversation_store.add_message(
            user_id=user_id,
            session_id=resolved_session_id,
            role="assistant",
            content=str(state.get("answer", "")),
            metadata={
                "intent": state.get("intent"),
                "actions": state.get("actions", []),
                "sources": state.get("sources", []),
                "quality": state["metadata"]["quality"],
                "topic_hint": retrieval_query if node_name in {"institutional_rag", "rag"} else None,
                "retrieval_query": retrieval_query if node_name in {"institutional_rag", "rag"} else None,
            },
        )
        state["metadata"]["assistant_message_id"] = assistant_record.message_id
        state["metadata"]["route"] = route
        return state


def route_node_label(intent: str) -> str:
    if intent in {"institutional_rag", "rag"}:
        return "rag_node"
    if intent in {"personal_memory", "memory"}:
        return "memory_node"
    return f"{intent}_node"

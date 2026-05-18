"""Build compact conversation context for routing and prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.services.conversation.conversation_schema import ConversationMessage
from backend.app.services.conversation.conversation_store import ConversationStore
from orchestration.assistant_brain import normalize_text


FOLLOWUP_REFERENCES = [
    "cai do",
    "nganh nay",
    "nganh do",
    "thay do",
    "co do",
    "no",
    "o tren",
    "vua roi",
    "noi tren",
    "chuong trinh nay",
    "mon do",
    "truong do",
]


@dataclass(frozen=True)
class ConversationContext:
    recent_messages: list[dict[str, Any]]
    conversation_summary: str
    has_followup_reference: bool
    last_topic_hint: str | None
    last_sources: list[dict[str, Any]] = field(default_factory=list)
    previous_intent: str | None = None

    def to_metadata(self) -> dict[str, Any]:
        return {
            "recent_messages": self.recent_messages,
            "conversation_summary": self.conversation_summary,
            "has_followup_reference": self.has_followup_reference,
            "last_topic_hint": self.last_topic_hint,
            "last_sources": self.last_sources,
            "previous_intent": self.previous_intent,
        }


class ConversationContextBuilder:
    def __init__(self, store: ConversationStore | None = None) -> None:
        self.store = store or ConversationStore()

    def build(
        self,
        *,
        user_id: str,
        session_id: str,
        current_message: str,
        limit: int = 10,
    ) -> ConversationContext:
        messages = self.store.get_recent_messages(user_id=user_id, session_id=session_id, limit=limit)
        normalized = normalize_text(current_message)
        return ConversationContext(
            recent_messages=[message.model_dump(mode="json") for message in messages],
            conversation_summary=self.store.get_session_summary(user_id=user_id, session_id=session_id),
            has_followup_reference=has_followup_reference(normalized),
            last_topic_hint=last_topic_hint(messages),
            last_sources=last_sources(messages),
            previous_intent=previous_intent(messages),
        )


def has_followup_reference(normalized_message: str) -> bool:
    return any(term in normalized_message for term in FOLLOWUP_REFERENCES)


def last_topic_hint(messages: list[ConversationMessage]) -> str | None:
    for message in reversed(messages):
        metadata = message.metadata or {}
        topic = metadata.get("topic_hint") or metadata.get("retrieval_query")
        if topic:
            return str(topic)
        if message.role == "user" and metadata.get("intent") in {"institutional_rag", "rag"}:
            return message.content
    return None


def last_sources(messages: list[ConversationMessage]) -> list[dict[str, Any]]:
    for message in reversed(messages):
        sources = (message.metadata or {}).get("sources")
        if isinstance(sources, list) and sources:
            return [item for item in sources if isinstance(item, dict)][:5]
    return []


def previous_intent(messages: list[ConversationMessage]) -> str | None:
    for message in reversed(messages):
        intent = (message.metadata or {}).get("intent")
        if intent:
            return str(intent)
    return None

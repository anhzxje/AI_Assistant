"""JSONL-backed conversation store.

The implementation is deliberately local-file first. Redis/Postgres can be
added behind the same methods later without changing orchestration code.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.config import get_backend_settings
from backend.app.services.conversation.conversation_schema import (
    ConversationMessage,
    ConversationRole,
    ConversationSession,
)


class ConversationStore:
    def __init__(self, root: Path | None = None) -> None:
        settings = get_backend_settings().data_settings
        self.root = root or settings.resolved_data_root / "personal_memory" / "conversations"
        self.root.mkdir(parents=True, exist_ok=True)

    def add_message(
        self,
        *,
        user_id: str,
        session_id: str,
        role: ConversationRole,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        record = ConversationMessage(
            message_id=str(uuid4()),
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        path = self._session_path(user_id=user_id, session_id=session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")
        return record

    def get_recent_messages(
        self,
        *,
        user_id: str,
        session_id: str,
        limit: int = 10,
    ) -> list[ConversationMessage]:
        messages = self._read_session(user_id=user_id, session_id=session_id)
        return messages[-limit:]

    def get_session_summary(self, *, user_id: str, session_id: str) -> str:
        messages = self._read_session(user_id=user_id, session_id=session_id)
        topic = latest_topic_hint(messages)
        turns = [message for message in messages if message.role in {"user", "assistant"}]
        if not turns:
            return ""
        summary_bits = []
        if topic:
            summary_bits.append(f"Last topic: {topic}")
        recent_user = [message.content for message in turns if message.role == "user"][-3:]
        if recent_user:
            summary_bits.append("Recent user questions: " + " | ".join(shorten(item, 140) for item in recent_user))
        return ". ".join(summary_bits)

    def list_sessions(self, *, user_id: str) -> list[ConversationSession]:
        user_root = self.root / safe_path_segment(user_id)
        if not user_root.exists():
            return []
        sessions: list[ConversationSession] = []
        for path in sorted(user_root.glob("*.jsonl")):
            session_id = path.stem
            messages = self._read_path(path)
            sessions.append(
                ConversationSession(
                    user_id=user_id,
                    session_id=session_id,
                    message_count=len(messages),
                    last_message_at=messages[-1].created_at if messages else None,
                    last_topic_hint=latest_topic_hint(messages),
                )
            )
        sessions.sort(key=lambda item: item.last_message_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return sessions

    def clear_session(self, *, user_id: str, session_id: str) -> bool:
        path = self._session_path(user_id=user_id, session_id=session_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def _session_path(self, *, user_id: str, session_id: str) -> Path:
        return self.root / safe_path_segment(user_id) / f"{safe_path_segment(session_id)}.jsonl"

    def _read_session(self, *, user_id: str, session_id: str) -> list[ConversationMessage]:
        return self._read_path(self._session_path(user_id=user_id, session_id=session_id))

    @staticmethod
    def _read_path(path: Path) -> list[ConversationMessage]:
        if not path.exists():
            return []
        messages: list[ConversationMessage] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                messages.append(ConversationMessage.model_validate_json(line))
            except Exception:
                continue
        return messages


def safe_path_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned[:120] or "default"


def latest_topic_hint(messages: list[ConversationMessage]) -> str | None:
    for message in reversed(messages):
        metadata = message.metadata or {}
        topic = metadata.get("topic_hint") or metadata.get("retrieval_query")
        if topic:
            return str(topic)
        if message.role == "user" and metadata.get("intent") in {"institutional_rag", "rag"}:
            return message.content
    return None


def shorten(value: str, limit: int) -> str:
    text = " ".join(value.split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."

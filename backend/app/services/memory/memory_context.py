"""Composition service for personal memory context."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.schemas.memory_schema import MemoryRecord, TaskRecord
from backend.app.services.memory.long_term_memory import LongTermMemoryStore
from backend.app.services.memory.semantic_memory import SemanticMemoryStore
from backend.app.services.memory.session_memory import SessionMemory
from backend.app.services.memory.task_memory import TaskMemoryStore


@dataclass(frozen=True)
class MemoryContext:
    recent_turns: list[dict]
    long_term_memories: list[MemoryRecord]
    semantic_memories: list[MemoryRecord]
    open_tasks: list[TaskRecord]

    @property
    def item_count(self) -> int:
        return (
            len(self.recent_turns)
            + len(self.long_term_memories)
            + len(self.semantic_memories)
            + len(self.open_tasks)
        )

    def to_prompt_block(self) -> str:
        blocks: list[str] = []
        if self.long_term_memories:
            lines = [f"- ({item.memory_type}) {item.content}" for item in self.long_term_memories[:6]]
            blocks.append("LONG_TERM_MEMORY:\n" + "\n".join(lines))
        if self.semantic_memories:
            lines = [f"- {item.content}" for item in self.semantic_memories[:4]]
            blocks.append("SEMANTIC_MEMORY:\n" + "\n".join(lines))
        if self.open_tasks:
            lines = [
                f"- [{item.priority}] {item.title}"
                + (f" | due: {item.due_date.isoformat()}" if item.due_date else "")
                for item in self.open_tasks[:6]
            ]
            blocks.append("OPEN_TASKS:\n" + "\n".join(lines))
        if self.recent_turns:
            lines = [f"- {turn.get('role')}: {turn.get('content')}" for turn in self.recent_turns[-6:]]
            blocks.append("RECENT_SESSION:\n" + "\n".join(lines))
        return "\n\n".join(blocks)


class MemoryContextService:
    def __init__(self) -> None:
        self._session_memory: SessionMemory | None = None
        self._long_term_memory: LongTermMemoryStore | None = None
        self._semantic_memory: SemanticMemoryStore | None = None
        self._task_memory: TaskMemoryStore | None = None

    @property
    def session_memory(self) -> SessionMemory:
        if self._session_memory is None:
            self._session_memory = SessionMemory()
        return self._session_memory

    @property
    def long_term_memory(self) -> LongTermMemoryStore:
        if self._long_term_memory is None:
            self._long_term_memory = LongTermMemoryStore()
        return self._long_term_memory

    @property
    def semantic_memory(self) -> SemanticMemoryStore:
        if self._semantic_memory is None:
            self._semantic_memory = SemanticMemoryStore()
        return self._semantic_memory

    @property
    def task_memory(self) -> TaskMemoryStore:
        if self._task_memory is None:
            self._task_memory = TaskMemoryStore()
        return self._task_memory

    def remember_text(
        self,
        *,
        user_id: str,
        text: str,
        memory_type: str,
        importance: float,
        source: str = "explicit",
    ) -> tuple[MemoryRecord, bool]:
        memory = self.long_term_memory.add_memory(
            user_id=user_id,
            content=text,
            memory_type=memory_type,
            importance=importance,
            source=source,
        )
        indexed = self.semantic_memory.index_memory(memory)
        return memory, indexed

    def build_context(self, *, user_id: str, query: str, session_id: str | None, limit: int = 8) -> MemoryContext:
        recent_turns = (
            self.session_memory.recent_turns(user_id=user_id, session_id=session_id, limit=6)
            if session_id
            else []
        )
        return MemoryContext(
            recent_turns=recent_turns,
            long_term_memories=self.long_term_memory.search(user_id=user_id, query=query, limit=limit),
            semantic_memories=self.semantic_memory.search(user_id=user_id, query=query, limit=min(5, limit)),
            open_tasks=self.task_memory.list_tasks(user_id=user_id, status="open", limit=8),
        )

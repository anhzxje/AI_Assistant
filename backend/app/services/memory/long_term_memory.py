"""Long-term user memory backed by PostgreSQL with JSONL fallback."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.config import get_backend_settings
from backend.app.schemas.memory_schema import MemoryRecord
from backend.app.services.memory.storage import append_jsonl, memory_data_root, read_jsonl, rewrite_jsonl


VALID_MEMORY_TYPES = {"preference", "recurring_task", "profile", "fact"}


class LongTermMemoryStore:
    def __init__(self) -> None:
        self.dsn = get_backend_settings().postgres_dsn
        self.fallback_path = memory_data_root() / "long_term_memories.jsonl"
        self._postgres_available = self._init_postgres()

    def add_memory(
        self,
        *,
        user_id: str,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.6,
        source: str = "explicit",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        now = datetime.now(timezone.utc)
        record = MemoryRecord(
            memory_id=str(uuid.uuid4()),
            user_id=user_id,
            memory_type=memory_type if memory_type in VALID_MEMORY_TYPES else "fact",
            content=content,
            importance=max(0.0, min(1.0, importance)),
            source=source,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        if self._postgres_available:
            try:
                self._insert_postgres(record)
                return record
            except Exception:
                self._postgres_available = False
        append_jsonl(self.fallback_path, record.model_dump(mode="json"))
        return record

    def search(self, *, user_id: str, query: str, limit: int = 8) -> list[MemoryRecord]:
        if self._postgres_available:
            try:
                return self._search_postgres(user_id=user_id, query=query, limit=limit)
            except Exception:
                self._postgres_available = False

        terms = tokenize(query)
        records = [
            MemoryRecord.model_validate(record)
            for record in read_jsonl(self.fallback_path)
            if record.get("user_id") == user_id
        ]
        records.sort(key=lambda item: (lexical_score(item.content, terms), item.importance), reverse=True)
        return [record for record in records if not terms or lexical_score(record.content, terms) > 0][:limit]

    def list_recent(self, *, user_id: str, limit: int = 20) -> list[MemoryRecord]:
        if self._postgres_available:
            try:
                return self._recent_postgres(user_id=user_id, limit=limit)
            except Exception:
                self._postgres_available = False
        records = [
            MemoryRecord.model_validate(record)
            for record in read_jsonl(self.fallback_path)
            if record.get("user_id") == user_id
        ]
        records.sort(key=lambda item: item.created_at, reverse=True)
        return records[:limit]

    def count(self, *, user_id: str) -> int:
        if self._postgres_available:
            try:
                return self._count_postgres(user_id=user_id)
            except Exception:
                self._postgres_available = False
        return sum(1 for record in read_jsonl(self.fallback_path) if record.get("user_id") == user_id)

    def delete(self, *, memory_id: str, user_id: str | None = None) -> bool:
        if self._postgres_available:
            try:
                deleted = self._delete_postgres(memory_id=memory_id, user_id=user_id)
                return deleted
            except Exception:
                self._postgres_available = False
        records = read_jsonl(self.fallback_path)
        kept = [
            record
            for record in records
            if not (
                record.get("memory_id") == memory_id
                and (user_id is None or record.get("user_id") == user_id)
            )
        ]
        deleted = len(kept) != len(records)
        if deleted:
            rewrite_jsonl(self.fallback_path, kept)
        return deleted

    def status(self) -> str:
        return "postgres" if self._postgres_available else "fallback"

    def _init_postgres(self) -> bool:
        try:
            import psycopg

            with psycopg.connect(self.dsn, connect_timeout=1) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_memories (
                        memory_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        importance DOUBLE PRECISION NOT NULL,
                        source TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories(user_id)")
                conn.commit()
            return True
        except Exception:
            return False

    def _insert_postgres(self, record: MemoryRecord) -> None:
        import psycopg

        with psycopg.connect(self.dsn, connect_timeout=1) as conn:
            conn.execute(
                """
                INSERT INTO user_memories (
                    memory_id, user_id, memory_type, content, importance, source,
                    created_at, updated_at, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    record.memory_id,
                    record.user_id,
                    record.memory_type,
                    record.content,
                    record.importance,
                    record.source,
                    record.created_at,
                    record.updated_at,
                    json.dumps(record.metadata, ensure_ascii=False),
                ),
            )
            conn.commit()

    def _search_postgres(self, *, user_id: str, query: str, limit: int) -> list[MemoryRecord]:
        import psycopg
        from psycopg.rows import dict_row

        like_query = f"%{query}%"
        with psycopg.connect(self.dsn, connect_timeout=1, row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT * FROM user_memories
                WHERE user_id = %s AND (content ILIKE %s OR memory_type ILIKE %s)
                ORDER BY importance DESC, created_at DESC
                LIMIT %s
                """,
                (user_id, like_query, like_query, limit),
            ).fetchall()
        return [MemoryRecord.model_validate(row) for row in rows]

    def _recent_postgres(self, *, user_id: str, limit: int) -> list[MemoryRecord]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self.dsn, connect_timeout=1, row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT * FROM user_memories
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            ).fetchall()
        return [MemoryRecord.model_validate(row) for row in rows]

    def _count_postgres(self, *, user_id: str) -> int:
        import psycopg

        with psycopg.connect(self.dsn, connect_timeout=1) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM user_memories WHERE user_id = %s",
                (user_id,),
            ).fetchone()
        return int(row[0]) if row else 0

    def _delete_postgres(self, *, memory_id: str, user_id: str | None) -> bool:
        import psycopg

        if user_id:
            query = "DELETE FROM user_memories WHERE memory_id = %s AND user_id = %s"
            params = (memory_id, user_id)
        else:
            query = "DELETE FROM user_memories WHERE memory_id = %s"
            params = (memory_id,)
        with psycopg.connect(self.dsn, connect_timeout=1) as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return bool(cursor.rowcount)


def tokenize(text: str) -> set[str]:
    return {token for token in text.lower().split() if len(token) >= 3}


def lexical_score(text: str, terms: set[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)

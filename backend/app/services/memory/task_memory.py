"""Task memory backed by PostgreSQL with JSONL fallback."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

from backend.app.config import get_backend_settings
from backend.app.schemas.memory_schema import TaskRecord
from backend.app.services.memory.storage import append_jsonl, memory_data_root, read_jsonl, rewrite_jsonl


VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"open", "in_progress", "done", "cancelled"}


class TaskMemoryStore:
    def __init__(self) -> None:
        self.dsn = get_backend_settings().postgres_dsn
        self.fallback_path = memory_data_root() / "tasks.jsonl"
        self._postgres_available = self._init_postgres()

    def add_task(
        self,
        *,
        user_id: str,
        title: str,
        due_date: date | None = None,
        priority: str = "medium",
        status: str = "open",
        source_text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskRecord:
        now = datetime.now(timezone.utc)
        record = TaskRecord(
            task_id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            due_date=due_date,
            priority=priority if priority in VALID_PRIORITIES else "medium",
            status=status if status in VALID_STATUSES else "open",
            source_text=source_text,
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

    def list_tasks(self, *, user_id: str, status: str | None = None, limit: int = 100) -> list[TaskRecord]:
        if self._postgres_available:
            try:
                return self._list_postgres(user_id=user_id, status=status, limit=limit)
            except Exception:
                self._postgres_available = False
        records = [
            TaskRecord.model_validate(record)
            for record in read_jsonl(self.fallback_path)
            if record.get("user_id") == user_id and (status is None or record.get("status") == status)
        ]
        records.sort(key=lambda item: (item.status != "open", item.due_date or date.max, item.created_at))
        return records[:limit]

    def count(self, *, user_id: str) -> int:
        if self._postgres_available:
            try:
                return self._count_postgres(user_id=user_id)
            except Exception:
                self._postgres_available = False
        return sum(1 for record in read_jsonl(self.fallback_path) if record.get("user_id") == user_id)

    def update_task(
        self,
        *,
        task_id: str,
        user_id: str | None = None,
        title: str | None = None,
        due_date: date | None = None,
        priority: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskRecord | None:
        updates = {
            "title": title,
            "due_date": due_date,
            "priority": priority if priority in VALID_PRIORITIES else None,
            "status": status if status in VALID_STATUSES else None,
            "metadata": metadata,
        }
        if self._postgres_available:
            try:
                return self._update_postgres(task_id=task_id, user_id=user_id, updates=updates)
            except Exception:
                self._postgres_available = False

        records = read_jsonl(self.fallback_path)
        updated: TaskRecord | None = None
        for record in records:
            if record.get("task_id") != task_id or (user_id is not None and record.get("user_id") != user_id):
                continue
            for key, value in updates.items():
                if value is not None:
                    record[key] = value.isoformat() if isinstance(value, date) else value
            record["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated = TaskRecord.model_validate(record)
        if updated:
            rewrite_jsonl(self.fallback_path, records)
        return updated

    def delete_task(self, *, task_id: str, user_id: str | None = None) -> bool:
        if self._postgres_available:
            try:
                return self._delete_postgres(task_id=task_id, user_id=user_id)
            except Exception:
                self._postgres_available = False
        records = read_jsonl(self.fallback_path)
        kept = [
            record
            for record in records
            if not (
                record.get("task_id") == task_id
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
                    CREATE TABLE IF NOT EXISTS user_tasks (
                        task_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        due_date DATE,
                        priority TEXT NOT NULL,
                        status TEXT NOT NULL,
                        source_text TEXT,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_tasks_user_status ON user_tasks(user_id, status)")
                conn.commit()
            return True
        except Exception:
            return False

    def _insert_postgres(self, record: TaskRecord) -> None:
        import psycopg

        with psycopg.connect(self.dsn, connect_timeout=1) as conn:
            conn.execute(
                """
                INSERT INTO user_tasks (
                    task_id, user_id, title, due_date, priority, status, source_text,
                    created_at, updated_at, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    record.task_id,
                    record.user_id,
                    record.title,
                    record.due_date,
                    record.priority,
                    record.status,
                    record.source_text,
                    record.created_at,
                    record.updated_at,
                    json.dumps(record.metadata, ensure_ascii=False),
                ),
            )
            conn.commit()

    def _list_postgres(self, *, user_id: str, status: str | None, limit: int) -> list[TaskRecord]:
        import psycopg
        from psycopg.rows import dict_row

        if status:
            query = """
                SELECT * FROM user_tasks
                WHERE user_id = %s AND status = %s
                ORDER BY due_date NULLS LAST, created_at DESC
                LIMIT %s
            """
            params = (user_id, status, limit)
        else:
            query = """
                SELECT * FROM user_tasks
                WHERE user_id = %s
                ORDER BY status, due_date NULLS LAST, created_at DESC
                LIMIT %s
            """
            params = (user_id, limit)
        with psycopg.connect(self.dsn, connect_timeout=1, row_factory=dict_row) as conn:
            rows = conn.execute(query, params).fetchall()
        return [TaskRecord.model_validate(row) for row in rows]

    def _count_postgres(self, *, user_id: str) -> int:
        import psycopg

        with psycopg.connect(self.dsn, connect_timeout=1) as conn:
            row = conn.execute("SELECT COUNT(*) FROM user_tasks WHERE user_id = %s", (user_id,)).fetchone()
        return int(row[0]) if row else 0

    def _update_postgres(
        self,
        *,
        task_id: str,
        user_id: str | None,
        updates: dict[str, Any],
    ) -> TaskRecord | None:
        import psycopg
        from psycopg.rows import dict_row

        assignments: list[str] = []
        values: list[Any] = []
        for key, value in updates.items():
            if value is None:
                continue
            if key == "metadata":
                assignments.append("metadata = %s::jsonb")
                values.append(json.dumps(value, ensure_ascii=False))
            else:
                assignments.append(f"{key} = %s")
                values.append(value)
        if not assignments:
            return self._get_postgres(task_id=task_id, user_id=user_id)
        assignments.append("updated_at = %s")
        values.append(datetime.now(timezone.utc))
        values.append(task_id)

        where = "task_id = %s"
        if user_id:
            where += " AND user_id = %s"
            values.append(user_id)
        query = f"UPDATE user_tasks SET {', '.join(assignments)} WHERE {where} RETURNING *"
        with psycopg.connect(self.dsn, connect_timeout=1, row_factory=dict_row) as conn:
            row = conn.execute(query, values).fetchone()
            conn.commit()
        return TaskRecord.model_validate(row) if row else None

    def _get_postgres(self, *, task_id: str, user_id: str | None) -> TaskRecord | None:
        import psycopg
        from psycopg.rows import dict_row

        where = "task_id = %s"
        params: tuple[Any, ...] = (task_id,)
        if user_id:
            where += " AND user_id = %s"
            params = (task_id, user_id)
        with psycopg.connect(self.dsn, connect_timeout=1, row_factory=dict_row) as conn:
            row = conn.execute(f"SELECT * FROM user_tasks WHERE {where}", params).fetchone()
        return TaskRecord.model_validate(row) if row else None

    def _delete_postgres(self, *, task_id: str, user_id: str | None) -> bool:
        import psycopg

        if user_id:
            query = "DELETE FROM user_tasks WHERE task_id = %s AND user_id = %s"
            params = (task_id, user_id)
        else:
            query = "DELETE FROM user_tasks WHERE task_id = %s"
            params = (task_id,)
        with psycopg.connect(self.dsn, connect_timeout=1) as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return bool(cursor.rowcount)

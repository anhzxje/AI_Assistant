"""Short-term conversation memory backed by Redis with in-process fallback."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from backend.app.config import get_backend_settings


class SessionMemory:
    def __init__(self) -> None:
        settings = get_backend_settings()
        self.redis_url = settings.redis_url
        self.ttl_seconds = settings.memory_session_ttl_seconds
        self.max_turns = settings.memory_session_max_turns
        self._fallback: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=self.max_turns))
        self._redis = self._connect_redis()

    def append_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        key = self._key(user_id=user_id, session_id=session_id)
        if self._redis is not None:
            self._redis.rpush(key, json.dumps(record, ensure_ascii=False))
            self._redis.ltrim(key, -self.max_turns, -1)
            self._redis.expire(key, self.ttl_seconds)
            return
        self._fallback[key].append(record)

    def recent_turns(self, *, user_id: str, session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        key = self._key(user_id=user_id, session_id=session_id)
        count = limit or self.max_turns
        if self._redis is not None:
            raw_items = self._redis.lrange(key, -count, -1)
            return [json.loads(item.decode("utf-8") if isinstance(item, bytes) else item) for item in raw_items]
        return list(self._fallback[key])[-count:]

    def status(self) -> str:
        return "redis" if self._redis is not None else "fallback"

    def _connect_redis(self):
        try:
            import redis

            client = redis.Redis.from_url(self.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
            client.ping()
            return client
        except Exception:
            return None

    @staticmethod
    def _key(*, user_id: str, session_id: str) -> str:
        safe_user_id = "".join(char if char.isalnum() or char in "._-" else "_" for char in user_id)[:160]
        safe_session_id = "".join(char if char.isalnum() or char in "._-" else "_" for char in session_id)[:160]
        return f"omni:session:{safe_user_id}:{safe_session_id}:turns"

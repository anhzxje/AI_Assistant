"""Small Redis-first cache with in-process TTL fallback."""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from threading import Lock
from typing import Any

from backend.app.config import get_backend_settings


class TTLCache:
    def __init__(self, *, namespace: str, max_items: int = 256) -> None:
        self.namespace = namespace
        self.max_items = max_items
        self._memory: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = Lock()
        self._redis = self._connect_redis()

    def get(self, key: str) -> Any | None:
        namespaced = self._key(key)
        if self._redis is not None:
            try:
                raw = self._redis.get(namespaced)
                return json.loads(raw) if raw else None
            except Exception:
                pass

        now = time.time()
        with self._lock:
            item = self._memory.get(namespaced)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._memory.pop(namespaced, None)
                return None
            self._memory.move_to_end(namespaced)
            return value

    def set(self, key: str, value: Any, *, ttl_seconds: int) -> None:
        namespaced = self._key(key)
        if self._redis is not None:
            try:
                self._redis.setex(namespaced, ttl_seconds, json.dumps(value, ensure_ascii=False, default=str))
                return
            except Exception:
                pass

        with self._lock:
            self._memory[namespaced] = (time.time() + ttl_seconds, value)
            self._memory.move_to_end(namespaced)
            while len(self._memory) > self.max_items:
                self._memory.popitem(last=False)

    def delete_prefix(self, prefix: str = "") -> int:
        namespaced_prefix = self._key(prefix)
        deleted = 0
        if self._redis is not None:
            try:
                for key in self._redis.scan_iter(f"{namespaced_prefix}*"):
                    deleted += int(self._redis.delete(key))
            except Exception:
                pass

        with self._lock:
            for key in list(self._memory):
                if key.startswith(namespaced_prefix):
                    self._memory.pop(key, None)
                    deleted += 1
        return deleted

    def _key(self, key: str) -> str:
        return f"omni:cache:{self.namespace}:{key}"

    def _connect_redis(self):
        try:
            import redis

            client = redis.Redis.from_url(get_backend_settings().redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
            client.ping()
            return client
        except Exception:
            return None

"""Semantic memory indexing and retrieval using Qdrant."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.config import get_backend_settings
from backend.app.schemas.memory_schema import MemoryRecord
from data_platform.feature_store.embeddings.embedding_model import LocalEmbeddingModel
from data_platform.feature_store.embeddings.qdrant_client_factory import create_qdrant_client


class SemanticMemoryStore:
    def __init__(self) -> None:
        settings = get_backend_settings()
        data_settings = settings.data_settings
        self.collection_name = settings.semantic_memory_collection
        self.embedding_model = LocalEmbeddingModel(
            model_name=data_settings.embedding_model_name,
            fallback_model_name=data_settings.embedding_fallback_model_name,
            device=data_settings.embedding_device,
        )
        self.client = None
        self._available = False
        try:
            self.client = create_qdrant_client(
                qdrant_url=data_settings.qdrant_url,
                local_path=data_settings.resolved_qdrant_memory_local_path,
            )
            self._available = True
        except Exception:
            self.client = None
            self._available = False

    def index_memory(self, memory: MemoryRecord) -> bool:
        if not self._available or self.client is None:
            return False
        try:
            from qdrant_client.models import PointStruct

            self._ensure_collection()
            vector = self.embedding_model.embed_passages([memory.content], batch_size=1)[0]
            payload = memory.model_dump(mode="json")
            payload["text"] = memory.content
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=stable_point_id(memory.memory_id),
                        vector=vector,
                        payload=payload,
                    )
                ],
                wait=True,
            )
            return True
        except Exception:
            self._available = False
            return False

    def add_conversation_summary(
        self,
        *,
        user_id: str,
        session_id: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        memory = MemoryRecord(
            memory_id=str(uuid.uuid4()),
            user_id=user_id,
            memory_type="conversation_summary",
            content=summary,
            importance=0.35,
            source="session_summary",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            metadata={"session_id": session_id, **(metadata or {})},
        )
        return self.index_memory(memory)

    def search(self, *, user_id: str, query: str, limit: int = 5) -> list[MemoryRecord]:
        if not self._available or self.client is None:
            return []
        try:
            self._ensure_collection()
            query_vector = self.embedding_model.embed_query(query)
            if hasattr(self.client, "search"):
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit * 3,
                    with_payload=True,
                    with_vectors=False,
                )
            else:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit * 3,
                    with_payload=True,
                    with_vectors=False,
                )
                hits = response.points
            records: list[MemoryRecord] = []
            for hit in hits:
                payload = hit.payload or {}
                if payload.get("user_id") == user_id:
                    records.append(MemoryRecord.model_validate(payload))
            return records[:limit]
        except Exception:
            self._available = False
            return []

    def status(self) -> str:
        return "qdrant" if self._available else "unavailable"

    def _ensure_collection(self) -> None:
        if self.client is None:
            return
        from qdrant_client.models import Distance, VectorParams

        info = self.embedding_model.info
        collections = self.client.get_collections().collections
        if any(collection.name == self.collection_name for collection in collections):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=info.vector_dimension, distance=Distance.COSINE),
        )


def stable_point_id(memory_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"memory:{memory_id}"))

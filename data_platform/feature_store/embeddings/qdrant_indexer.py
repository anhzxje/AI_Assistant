"""Qdrant indexing for chunk embeddings."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data_platform.feature_store.embeddings.embedding_model import LocalEmbeddingModel
from data_platform.feature_store.embeddings.qdrant_client_factory import create_qdrant_client


@dataclass(frozen=True)
class IndexStats:
    chunks_read: int
    chunks_indexed: int
    skipped_existing_chunks: int
    embedding_model: str
    vector_dimension: int
    collection_name: str


class QdrantChunkIndexer:
    def __init__(
        self,
        *,
        qdrant_url: str,
        collection_name: str,
        embedding_model: LocalEmbeddingModel,
        local_path: Path | None = None,
    ) -> None:
        try:
            import qdrant_client  # noqa: F401
        except ModuleNotFoundError as exc:
            raise RuntimeError("qdrant-client is required. Install with `python -m pip install qdrant-client`.") from exc

        self.client = create_qdrant_client(qdrant_url=qdrant_url, local_path=local_path)
        self.collection_name = collection_name
        self.embedding_model = embedding_model

    def index_file(self, path: Path, *, batch_size: int = 32, recreate: bool = False) -> IndexStats:
        chunks = read_jsonl(path)
        model_info = self.embedding_model.info
        if recreate:
            self._recreate_collection(model_info.vector_dimension)
        else:
            self._ensure_collection(model_info.vector_dimension)

        existing_chunk_ids = self._existing_chunk_ids()
        to_index = [
            chunk
            for chunk in chunks
            if str(chunk.get("chunk_id") or "") not in existing_chunk_ids
        ]

        indexed = 0
        for start in range(0, len(to_index), batch_size):
            batch = to_index[start : start + batch_size]
            vectors = self.embedding_model.embed_passages(
                [str(item.get("text") or "") for item in batch],
                batch_size=batch_size,
            )
            self._upsert_batch(batch, vectors, model_info.model_name, model_info.vector_dimension)
            indexed += len(batch)

        return IndexStats(
            chunks_read=len(chunks),
            chunks_indexed=indexed,
            skipped_existing_chunks=len(chunks) - len(to_index),
            embedding_model=model_info.model_name,
            vector_dimension=model_info.vector_dimension,
            collection_name=self.collection_name,
        )

    def _ensure_collection(self, vector_dimension: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        collections = self.client.get_collections().collections
        if any(collection.name == self.collection_name for collection in collections):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_dimension, distance=Distance.COSINE),
        )

    def _recreate_collection(self, vector_dimension: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        collections = self.client.get_collections().collections
        if any(collection.name == self.collection_name for collection in collections):
            self.client.delete_collection(collection_name=self.collection_name)
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_dimension, distance=Distance.COSINE),
        )

    def _existing_chunk_ids(self) -> set[str]:
        chunk_ids: set[str] = set()
        offset = None
        while True:
            records, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=256,
                offset=offset,
                with_payload=["chunk_id"],
                with_vectors=False,
            )
            for record in records:
                payload = record.payload or {}
                chunk_id = payload.get("chunk_id")
                if chunk_id:
                    chunk_ids.add(str(chunk_id))
            if offset is None:
                break
        return chunk_ids

    def _upsert_batch(
        self,
        chunks: list[dict[str, Any]],
        vectors: list[list[float]],
        model_name: str,
        vector_dimension: int,
    ) -> None:
        from qdrant_client.models import PointStruct

        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            payload = build_payload(chunk)
            payload["embedding_model"] = model_name
            payload["vector_dimension"] = vector_dimension
            points.append(
                PointStruct(
                    id=stable_point_id(str(chunk["chunk_id"])),
                    vector=vector,
                    payload=payload,
                )
            )
        self.client.upsert(collection_name=self.collection_name, points=points, wait=True)


def build_payload(chunk: dict[str, Any]) -> dict[str, Any]:
    features = chunk.get("features") or {}
    return {
        "chunk_id": chunk.get("chunk_id"),
        "document_id": chunk.get("document_id"),
        "title": chunk.get("title"),
        "source_url": chunk.get("source_url"),
        "source_path": chunk.get("source_path"),
        "document_type": chunk.get("document_type"),
        "chunk_index": chunk.get("chunk_index"),
        "text": chunk.get("text"),
        "chunk_text_full": chunk.get("chunk_text_full") or chunk.get("text"),
        "preview_text": chunk.get("preview_text") or features.get("preview_text"),
        "context_before": chunk.get("context_before") or (chunk.get("metadata") or {}).get("context_before"),
        "context_after": chunk.get("context_after") or (chunk.get("metadata") or {}).get("context_after"),
        "keyword_hints": features.get("keyword_hints", []),
        "freshness_score": float(features.get("freshness_score") or 0.0),
        "authority_score": float(features.get("authority_score") or 0.0),
        "boilerplate_score": float(features.get("boilerplate_score") or 0.0),
        "menu_density_score": float(features.get("menu_density_score") or 0.0),
        "content_quality_score": float(features.get("content_quality_score") or 0.5),
        "section_heading": chunk.get("section_heading") or features.get("section_heading"),
        "entity_mentions": features.get("entity_mentions", []),
        "content_hash": chunk.get("content_hash"),
        "published_date": (chunk.get("metadata") or {}).get("published_date"),
        "citation": {
            "title": chunk.get("title"),
            "source_url": chunk.get("source_url"),
            "chunk_id": chunk.get("chunk_id"),
            "document_type": chunk.get("document_type"),
        },
    }


def stable_point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

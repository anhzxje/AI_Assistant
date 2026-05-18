"""Service wrapper around Qdrant retriever."""

from __future__ import annotations

from functools import lru_cache
from dataclasses import asdict

from backend.app.config import get_backend_settings
from backend.app.services.cache import TTLCache
from data_platform.processing.cleaners.text_cleaner import normalize_for_match
from data_platform.feature_store.embeddings.embedding_model import LocalEmbeddingModel
from data_platform.feature_store.embeddings.qdrant_client_factory import create_qdrant_client
from data_platform.feature_store.embeddings.retriever import QdrantRetriever, RetrievalResult


RETRIEVAL_CACHE_VERSION = "v2"


class RetrieverService:
    def __init__(self) -> None:
        settings = get_backend_settings()
        data_settings = settings.data_settings
        self.collection = data_settings.qdrant_collection
        self.embedding_model = LocalEmbeddingModel(
            model_name=data_settings.embedding_model_name,
            fallback_model_name=data_settings.embedding_fallback_model_name,
            device=data_settings.embedding_device,
        )
        self.retriever = QdrantRetriever(
            qdrant_url=data_settings.qdrant_url,
            collection_name=self.collection,
            embedding_model=self.embedding_model,
            local_path=data_settings.resolved_qdrant_local_path,
        )
        self.cache = TTLCache(namespace="retrieval", max_items=256)
        self.cache_ttl_seconds = settings.omni_retrieval_cache_ttl_sec
        self.last_timings: dict[str, int | bool] = {}

    @property
    def embedding_model_name(self) -> str:
        return self.embedding_model.info.model_name

    def retrieve(self, query: str, *, top_k: int) -> list[RetrievalResult]:
        key = self._cache_key(query=query, top_k=top_k)
        cached = self.cache.get(key)
        if cached:
            self.last_timings = {"cache_hit": True, "embedding_latency_ms": 0, "qdrant_latency_ms": 0, "reranking_latency_ms": 0}
            return [RetrievalResult(**item) for item in cached]
        results = self.retriever.retrieve(query, top_k=top_k)
        self.last_timings = {"cache_hit": False, **self.retriever.last_timings}
        self.cache.set(key, [asdict(result) for result in results], ttl_seconds=self.cache_ttl_seconds)
        return results

    def clear_cache(self) -> int:
        return self.cache.delete_prefix()

    def _cache_key(self, *, query: str, top_k: int) -> str:
        return f"{RETRIEVAL_CACHE_VERSION}:{self.collection}:top{top_k}:{normalize_for_match(query)}"


@lru_cache(maxsize=1)
def get_retriever_service() -> RetrieverService:
    return RetrieverService()


def clear_retrieval_cache() -> int:
    return get_retriever_service().clear_cache()


def qdrant_status() -> str:
    settings = get_backend_settings().data_settings
    try:
        client = create_qdrant_client(
            qdrant_url=settings.qdrant_url,
            local_path=None,
        )
        client.get_collections()
        return "available"
    except Exception:
        if settings.resolved_qdrant_local_path.exists():
            return "embedded"
        return "unavailable"

"""Sentence-transformers embedding model wrapper."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from collections import OrderedDict
from threading import Lock
import time

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingModelInfo:
    model_name: str
    device: str
    vector_dimension: int
    normalize_embeddings: bool


class LocalEmbeddingModel:
    """Lazy sentence-transformers wrapper with CPU fallback and E5 query/passages prefixes."""

    def __init__(
        self,
        *,
        model_name: str,
        fallback_model_name: str,
        device: str = "auto",
        normalize_embeddings: bool = True,
    ) -> None:
        self.requested_model_name = model_name
        self.fallback_model_name = fallback_model_name
        self.device = resolve_device(device)
        self.normalize_embeddings = normalize_embeddings
        self._model = None
        self._actual_model_name: str | None = None
        self._dimension: int | None = None
        self._query_cache: OrderedDict[str, tuple[float, list[float]]] = OrderedDict()
        self._cache_lock = Lock()
        self._query_cache_ttl_seconds = 3600
        self._query_cache_max_items = 512

    @property
    def info(self) -> EmbeddingModelInfo:
        self._ensure_loaded()
        return EmbeddingModelInfo(
            model_name=self._actual_model_name or self.requested_model_name,
            device=self.device,
            vector_dimension=int(self._dimension or 0),
            normalize_embeddings=self.normalize_embeddings,
        )

    def embed_passages(self, texts: list[str], *, batch_size: int = 32) -> list[list[float]]:
        prepared = [self._format_passage(text) for text in texts]
        return self._encode(prepared, batch_size=batch_size)

    def embed_query(self, query: str) -> list[float]:
        cache_key = " ".join(query.lower().split())
        cached = self._get_cached_query(cache_key)
        if cached is not None:
            return cached
        vector = self._encode([self._format_query(query)], batch_size=1)[0]
        self._set_cached_query(cache_key, vector)
        return vector

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "sentence-transformers is required for embeddings. "
                "Install with `python -m pip install sentence-transformers qdrant-client`."
            ) from exc

        try:
            self._model = self._load_sentence_transformer(SentenceTransformer, self.requested_model_name)
            self._actual_model_name = self.requested_model_name
        except Exception as exc:  # noqa: BLE001 - model download/load fallback is intentional.
            logger.warning(
                "Could not load embedding model %s: %s. Falling back to %s",
                self.requested_model_name,
                exc,
                self.fallback_model_name,
            )
            self._model = self._load_sentence_transformer(SentenceTransformer, self.fallback_model_name)
            self._actual_model_name = self.fallback_model_name

        self._dimension = int(self._model.get_sentence_embedding_dimension())

    def _load_sentence_transformer(self, sentence_transformer_cls: object, model_name: str):
        try:
            return sentence_transformer_cls(model_name, device=self.device)
        except Exception as exc:  # noqa: BLE001 - cached local retry avoids network requirement after first download.
            logger.info("Retrying embedding model %s with local_files_only=True after: %s", model_name, exc)
            return sentence_transformer_cls(model_name, device=self.device, local_files_only=True)

    def _encode(self, texts: list[str], *, batch_size: int) -> list[list[float]]:
        self._ensure_loaded()
        vectors = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vectors = np.asarray(vectors, dtype=np.float32)
        return vectors.tolist()

    def _get_cached_query(self, cache_key: str) -> list[float] | None:
        now = time.time()
        with self._cache_lock:
            item = self._query_cache.get(cache_key)
            if item is None:
                return None
            expires_at, vector = item
            if expires_at <= now:
                self._query_cache.pop(cache_key, None)
                return None
            self._query_cache.move_to_end(cache_key)
            return vector

    def _set_cached_query(self, cache_key: str, vector: list[float]) -> None:
        with self._cache_lock:
            self._query_cache[cache_key] = (time.time() + self._query_cache_ttl_seconds, vector)
            self._query_cache.move_to_end(cache_key)
            while len(self._query_cache) > self._query_cache_max_items:
                self._query_cache.popitem(last=False)

    def _format_passage(self, text: str) -> str:
        if "e5" in self.info.model_name.lower():
            return f"passage: {text}"
        return text

    def _format_query(self, query: str) -> str:
        if "e5" in self.info.model_name.lower():
            return f"query: {query}"
        return query


def resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # noqa: BLE001 - torch may be missing before sentence-transformers install.
        return "cpu"

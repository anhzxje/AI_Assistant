"""Qdrant client creation with local embedded fallback."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def create_qdrant_client(*, qdrant_url: str, local_path: Path | None = None):
    from qdrant_client import QdrantClient

    if local_path is None:
        return QdrantClient(url=qdrant_url)

    try:
        client = QdrantClient(url=qdrant_url)
        client.get_collections()
        return client
    except Exception as exc:  # noqa: BLE001 - local fallback keeps development unblocked.
        logger.warning(
            "Qdrant server at %s is unavailable: %s. Falling back to local path %s",
            qdrant_url,
            exc,
            local_path,
        )
        local_path.mkdir(parents=True, exist_ok=True)
        return QdrantClient(path=str(local_path))

"""Embed chunk records and index them into Qdrant."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_platform.config import get_settings
from data_platform.feature_store.embeddings.embedding_model import LocalEmbeddingModel
from data_platform.feature_store.embeddings.qdrant_indexer import QdrantChunkIndexer
from data_platform.logging_utils import configure_logging
from backend.app.services.cache import TTLCache


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index chunk embeddings into Qdrant.")
    parser.add_argument("--latest", action="store_true", help="Use latest document_chunks.jsonl.")
    parser.add_argument("--input", type=Path, default=None, help="Explicit chunks JSONL path.")
    parser.add_argument("--collection", type=str, default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate collection before indexing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    input_path = resolve_input_path(args, settings.resolved_data_root)
    collection = args.collection or settings.qdrant_collection
    model = LocalEmbeddingModel(
        model_name=settings.embedding_model_name,
        fallback_model_name=settings.embedding_fallback_model_name,
        device=settings.embedding_device,
    )
    indexer = QdrantChunkIndexer(
        qdrant_url=settings.qdrant_url,
        collection_name=collection,
        embedding_model=model,
        local_path=settings.resolved_qdrant_local_path,
    )
    stats = indexer.index_file(input_path, batch_size=args.batch_size, recreate=args.recreate)
    retrieval_deleted = TTLCache(namespace="retrieval").delete_prefix()
    answer_deleted = TTLCache(namespace="answer").delete_prefix()

    print("Qdrant indexing complete")
    print(f"chunks_read={stats.chunks_read}")
    print(f"chunks_indexed={stats.chunks_indexed}")
    print(f"skipped_existing_chunks={stats.skipped_existing_chunks}")
    print(f"embedding_model={stats.embedding_model}")
    print(f"vector_dimension={stats.vector_dimension}")
    print(f"collection_name={stats.collection_name}")
    print(f"retrieval_cache_deleted={retrieval_deleted}")
    print(f"answer_cache_deleted={answer_deleted}")


def resolve_input_path(args: argparse.Namespace, data_root: Path) -> Path:
    if args.input:
        return (PROJECT_ROOT / args.input).resolve() if not args.input.is_absolute() else args.input
    if args.latest:
        candidates = sorted((data_root / "features" / "chunks").glob("*/document_chunks.jsonl"))
        if not candidates:
            raise FileNotFoundError("No document_chunks.jsonl found under data/features/chunks")
        return candidates[-1]
    raise ValueError("Pass --latest or --input path")


if __name__ == "__main__":
    main()

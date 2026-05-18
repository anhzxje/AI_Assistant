"""Run a semantic retrieval test query against Qdrant."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_platform.config import get_settings
from data_platform.feature_store.embeddings.embedding_model import LocalEmbeddingModel
from data_platform.feature_store.embeddings.retriever import QdrantRetriever
from data_platform.logging_utils import configure_logging


def readable_preview(text: str, *, max_chars: int = 360) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    clipped = normalized[: max_chars + 1].rstrip()
    boundary = max(clipped.rfind(" "), clipped.rfind("."), clipped.rfind(";"), clipped.rfind(":"), clipped.rfind(","))
    if boundary >= int(max_chars * 0.65):
        clipped = clipped[:boundary].rstrip(" ,;:")
    else:
        clipped = clipped[:max_chars].rstrip()
    return f"{clipped}…"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve top-k chunks from Qdrant.")
    parser.add_argument("query", type=str)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--collection", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    model = LocalEmbeddingModel(
        model_name=settings.embedding_model_name,
        fallback_model_name=settings.embedding_fallback_model_name,
        device=settings.embedding_device,
    )
    retriever = QdrantRetriever(
        qdrant_url=settings.qdrant_url,
        collection_name=args.collection or settings.qdrant_collection,
        embedding_model=model,
        local_path=settings.resolved_qdrant_local_path,
    )
    results = retriever.retrieve(args.query, top_k=args.top_k)

    print(f"query={args.query}")
    for index, result in enumerate(results, start=1):
        preview_text = str(result.payload.get("preview_text") or result.text)
        preview = readable_preview(preview_text)
        print(f"rank={index}")
        print(f"  title={result.title}")
        print(f"  document_type={result.document_type}")
        print(f"  score={result.score} vector_score={result.vector_score}")
        print(f"  source_url={result.source_url}")
        if result.payload.get("section_heading"):
            print(f"  section_heading={result.payload.get('section_heading')}")
        print(f"  preview={preview}")


if __name__ == "__main__":
    main()

"""Build chunk-level retrieval features from processed documents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_platform.config import get_settings
from data_platform.feature_store.chunk_store import JsonlChunkStore
from data_platform.feature_store.feature_builder import FeatureBuilder, latest_processed_documents_path
from data_platform.logging_utils import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build chunk features from processed documents.")
    parser.add_argument("--latest", action="store_true", help="Use latest processed_documents.jsonl.")
    parser.add_argument("--input", type=Path, default=None, help="Explicit processed JSONL path.")
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    input_path = resolve_input_path(args, settings.resolved_data_root)
    date_partition = input_path.parent.name

    chunks_path = (
        settings.resolved_data_root
        / "features"
        / "chunks"
        / date_partition
        / "document_chunks.jsonl"
    )
    summary_path = (
        settings.resolved_data_root
        / "features"
        / "metadata"
        / date_partition
        / "feature_summary.json"
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    documents = read_jsonl(input_path)
    builder = FeatureBuilder(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    chunks, summary = builder.build_chunks(documents)

    JsonlChunkStore(chunks_path).write_all(chunks)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Feature build complete")
    print(f"documents_read={len(documents)}")
    print(f"chunks_written={len(chunks)}")
    print(f"average_chunk_length={summary['average_chunk_length']}")
    print(f"chunks_by_document_type={summary['chunks_by_document_type']}")
    print(f"chunks_output_path={chunks_path}")
    print(f"summary_output_path={summary_path}")
    for index, chunk in enumerate(chunks[:3], start=1):
        print(
            f"sample_{index}=title={chunk.title!r} "
            f"type={chunk.document_type} "
            f"keyword_hints={chunk.features['keyword_hints']} "
            f"entity_mentions={chunk.features['entity_mentions'][:5]}"
        )


def resolve_input_path(args: argparse.Namespace, data_root: Path) -> Path:
    if args.input:
        return (PROJECT_ROOT / args.input).resolve() if not args.input.is_absolute() else args.input
    if args.latest:
        return latest_processed_documents_path(data_root)
    raise ValueError("Pass --latest or --input path")


def read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


if __name__ == "__main__":
    main()

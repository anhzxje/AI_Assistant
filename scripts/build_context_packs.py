"""Build compact LLM context packs from the latest feature chunks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_platform.config import get_settings
from data_platform.feature_store.context_pack_builder import build_context_packs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build topic context packs for LLM/admin review.")
    parser.add_argument("--latest", action="store_true", help="Use latest document_chunks.jsonl.")
    parser.add_argument("--input", type=Path, default=None, help="Explicit chunk JSONL path.")
    parser.add_argument("--max-facts", type=int, default=8, help="Maximum facts per topic.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    chunks_path = resolve_input_path(args, settings.resolved_data_root)
    date_partition = chunks_path.parent.name
    output_dir = settings.resolved_data_root / "features" / "context_packs" / date_partition
    packs = build_context_packs(chunks_path, output_dir, max_facts_per_topic=args.max_facts)

    print("Context pack build complete")
    print(f"chunks_input_path={chunks_path}")
    print(f"output_dir={output_dir}")
    for pack in packs:
        print(
            f"topic={pack.topic} facts={len(pack.trusted_facts)} "
            f"sources={len(pack.source_citations)} gaps={len(pack.gaps)}"
        )


def resolve_input_path(args: argparse.Namespace, data_root: Path) -> Path:
    if args.input:
        return (PROJECT_ROOT / args.input).resolve() if not args.input.is_absolute() else args.input
    if args.latest:
        chunk_root = data_root / "features" / "chunks"
        candidates = sorted(chunk_root.glob("*/document_chunks.jsonl"), key=lambda path: path.parent.name)
        if not candidates:
            raise FileNotFoundError(f"No chunk files found below {chunk_root}")
        return candidates[-1]
    raise ValueError("Pass --latest or --input path")


if __name__ == "__main__":
    main()

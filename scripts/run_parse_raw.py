"""Parse raw crawled HTML/PDF artifacts into processed document JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_platform.config import get_settings
from data_platform.governance.hashing import sha256_bytes
from data_platform.ingestion.parsers.html_parser import parse_html_file
from data_platform.ingestion.parsers.pdf_parser import PdfParserUnavailable, parse_pdf_file
from data_platform.logging_utils import configure_logging
from data_platform.processing.cleaners.text_cleaner import detect_language, has_enough_text
from data_platform.processing.extractors.date_extractor import extract_published_date
from data_platform.processing.extractors.document_classifier import classify_document


@dataclass(frozen=True)
class ProcessedDocument:
    document_id: str
    source_url: str
    source_path: str
    source_type: str
    title: str | None
    text: str
    headings: list[str]
    tables: list[Any]
    links: list[dict[str, str]]
    language: str
    document_type: str
    published_date: str | None
    processed_time: str
    content_hash: str
    raw_content_hash: str
    metadata: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse raw crawl artifacts into processed JSONL.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum manifest records to parse.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/metadata/crawl_manifest.jsonl"),
        help="Path to crawl manifest JSONL.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Output date partition. Defaults to today's UTC date.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    output_date = args.date or datetime.now(timezone.utc).date().isoformat()
    output_path = (
        settings.resolved_data_root
        / "processed"
        / "documents"
        / output_date
        / "processed_documents.jsonl"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = read_manifest_records(PROJECT_ROOT / args.manifest)
    raw_records_read = 0
    written = 0
    skipped = 0
    skip_reasons: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    samples: list[tuple[str | None, str, int]] = []
    seen_raw_hashes: set[str] = set()
    seen_content_hashes: set[str] = set()

    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        for record in records:
            if raw_records_read >= args.limit:
                break
            status = str(record.get("status", ""))
            if status not in {"fetched_html", "downloaded_pdf", "copied_local_pdf"}:
                continue

            raw_records_read += 1
            raw_hash = str(record.get("content_hash", ""))
            if raw_hash and raw_hash in seen_raw_hashes:
                skipped += 1
                skip_reasons["duplicate_raw_hash"] += 1
                continue
            if raw_hash:
                seen_raw_hashes.add(raw_hash)

            try:
                processed = process_record(record)
            except PdfParserUnavailable as exc:
                skipped += 1
                skip_reasons["pdf_parser_unavailable"] += 1
                print(f"skip_pdf_parser_unavailable={record.get('saved_path')} reason={exc}")
                continue
            except Exception as exc:  # noqa: BLE001 - CLI should continue parsing other docs.
                skipped += 1
                skip_reasons["parse_error"] += 1
                print(f"skip_parse_error={record.get('saved_path')} reason={exc!r}")
                continue

            if not has_enough_text(processed.text):
                skipped += 1
                skip_reasons["too_little_text"] += 1
                continue
            if processed.content_hash in seen_content_hashes:
                skipped += 1
                skip_reasons["duplicate_content_hash"] += 1
                continue
            seen_content_hashes.add(processed.content_hash)

            output_file.write(json.dumps(asdict(processed), ensure_ascii=False))
            output_file.write("\n")
            written += 1
            type_counts[processed.document_type] += 1
            if len(samples) < 3:
                samples.append((processed.title, processed.document_type, len(processed.text)))

    print("Raw parse complete")
    print(f"raw_records_read={raw_records_read}")
    print(f"processed_documents_written={written}")
    print(f"skipped_documents={skipped}")
    print(f"skip_reasons={dict(skip_reasons)}")
    print(f"document_type_counts={dict(type_counts)}")
    print(f"output_path={output_path}")
    for index, (title, document_type, text_length) in enumerate(samples, start=1):
        print(
            f"sample_{index}=title={title!r} "
            f"document_type={document_type} text_length={text_length}"
        )


def read_manifest_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def process_record(record: dict[str, Any]) -> ProcessedDocument:
    source_path = PROJECT_ROOT / str(record["saved_path"])
    source_url = str(record.get("url") or "")
    source_type = "pdf" if str(record.get("content_type", "")).startswith("application/pdf") else "html"

    if source_type == "html":
        parsed_html = parse_html_file(source_path, source_url)
        title = parsed_html.title or record.get("title")
        text = parsed_html.text
        headings = parsed_html.headings
        tables = parsed_html.tables
        links = parsed_html.links
        metadata: dict[str, Any] = {"parser": "beautifulsoup"}
    else:
        parsed_pdf = parse_pdf_file(source_path)
        title = parsed_pdf.title or record.get("title") or source_path.stem
        text = parsed_pdf.text
        headings = []
        tables = []
        links = []
        metadata = {
            "parser": "pymupdf",
            "page_count": parsed_pdf.page_count,
            "pages": parsed_pdf.pages,
            "pdf_metadata": parsed_pdf.metadata,
        }

    content_hash = sha256_bytes(text.encode("utf-8"))
    document_type = classify_document(url=source_url, title=str(title or ""), text=text)
    document_identity_hash = sha256_bytes(
        "|".join(
            [
                source_url,
                str(source_path.relative_to(PROJECT_ROOT)),
                str(record.get("content_hash") or ""),
                content_hash,
            ]
        ).encode("utf-8")
    )
    return ProcessedDocument(
        document_id=f"doc_{document_identity_hash[:20]}",
        source_url=source_url,
        source_path=str(source_path.relative_to(PROJECT_ROOT)),
        source_type=source_type,
        title=str(title) if title else None,
        text=text,
        headings=headings,
        tables=tables,
        links=links,
        language=detect_language(text),
        document_type=document_type,
        published_date=extract_published_date(text),
        processed_time=datetime.now(timezone.utc).isoformat(),
        content_hash=content_hash,
        raw_content_hash=str(record.get("content_hash") or ""),
        metadata=metadata,
    )


if __name__ == "__main__":
    main()

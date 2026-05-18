"""Feature engineering for processed institutional documents."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from data_platform.feature_store.chunk_store import DocumentChunkRecord
from data_platform.governance.hashing import sha256_bytes
from data_platform.processing.chunkers.text_chunker import chunk_text
from data_platform.processing.cleaners.text_cleaner import (
    boilerplate_score,
    content_quality_score,
    menu_density_score,
    normalize_for_match,
)
from data_platform.processing.extractors.entity_extractor import extract_entity_mentions

KEYWORD_HINTS = (
    "tuyen sinh",
    "chuong trinh dao tao",
    "hoc phi",
    "hoc bong",
    "giang vien",
    "can bo",
    "thong bao",
    "quy che",
    "thac si",
    "tien si",
    "khoa hoc du lieu",
    "khoa hoc may tinh",
    "toan tin",
    "lich thi",
    "lich hoc",
    "hieu truong",
    "pho hieu truong",
    "ban giam hieu",
    "lanh dao",
    "hoi dong truong",
)


class FeatureBuilder:
    def __init__(self, *, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def build_chunks(self, documents: list[dict]) -> tuple[list[DocumentChunkRecord], dict]:
        records: list[DocumentChunkRecord] = []
        skipped = 0
        skipped_duplicate_exact_sources = 0
        unique_documents: list[dict] = []
        seen_exact_sources: set[tuple[str, str, str, str]] = set()

        for document in documents:
            exact_source_key = (
                str(document.get("source_url") or ""),
                str(document.get("source_path") or ""),
                str(document.get("raw_content_hash") or ""),
                str(document.get("content_hash") or ""),
            )
            if exact_source_key in seen_exact_sources:
                skipped += 1
                skipped_duplicate_exact_sources += 1
                continue
            seen_exact_sources.add(exact_source_key)
            unique_documents.append(document)

            text = str(document.get("text") or "")
            chunks = chunk_text(
                text,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            if not chunks:
                skipped += 1
                continue

            for chunk in chunks:
                section_heading = infer_section_heading(document, chunk.text)
                keyword_hints = extract_keyword_hints(
                    " ".join(
                        [
                            str(document.get("title") or ""),
                            chunk.text,
                        ]
                    )
                )
                entity_mentions = extract_entity_mentions(chunk.text)
                source_url = str(document.get("source_url") or "")
                chunk_id = stable_chunk_id(
                    str(document["document_id"]),
                    str(document.get("source_path") or ""),
                    source_url,
                    chunk.chunk_index,
                    chunk.content_hash,
                )
                records.append(
                    DocumentChunkRecord(
                        chunk_id=chunk_id,
                        document_id=str(document["document_id"]),
                        source_url=source_url,
                        source_path=str(document.get("source_path") or ""),
                        title=document.get("title"),
                        document_type=str(document.get("document_type") or "unknown"),
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        character_start=chunk.character_start,
                        character_end=chunk.character_end,
                        content_hash=chunk.content_hash,
                        chunk_text_full=chunk.text,
                        preview_text=chunk.preview_text,
                        section_heading=section_heading,
                        context_before=chunk.context_before,
                        context_after=chunk.context_after,
                        features={
                            "text_length": len(chunk.text),
                            "keyword_hints": keyword_hints,
                            "freshness_score": freshness_score(
                                document.get("published_date"),
                                str(document.get("document_type") or "unknown"),
                            ),
                            "authority_score": authority_score(source_url),
                            "entity_mentions": entity_mentions,
                            "boilerplate_score": boilerplate_score(chunk.text),
                            "menu_density_score": menu_density_score(chunk.text),
                            "content_quality_score": content_quality_score(chunk.text),
                            "section_heading": section_heading,
                            "preview_text": chunk.preview_text,
                        },
                        metadata={
                            "source_type": document.get("source_type"),
                            "language": document.get("language"),
                            "raw_content_hash": document.get("raw_content_hash"),
                            "published_date": document.get("published_date"),
                            "context_before": chunk.context_before,
                            "context_after": chunk.context_after,
                        },
                    )
                )

        summary = build_summary(unique_documents, records, skipped)
        summary["skipped_duplicate_exact_sources"] = skipped_duplicate_exact_sources
        summary["input_documents"] = len(documents)
        return records, summary


def extract_keyword_hints(text: str) -> list[str]:
    lowered = normalize_for_match(text)
    return [keyword for keyword in KEYWORD_HINTS if keyword in lowered]


def infer_section_heading(document: dict, chunk_text_value: str) -> str | None:
    headings = document.get("headings") or []
    normalized_chunk = normalize_for_match(chunk_text_value[:1200])
    if headings:
        for heading in reversed(headings[:12]):
            if heading and normalize_for_match(str(heading)) in normalized_chunk:
                return str(heading)
        return str(headings[0])
    title = document.get("title")
    return str(title) if title else None


def freshness_score(published_date: object, document_type: str) -> float:
    if not published_date:
        return 0.45 if document_type in {"regulation", "curriculum", "program", "leadership"} else 0.3
    try:
        parsed = date.fromisoformat(str(published_date))
    except ValueError:
        return 0.3

    age_days = (datetime.now(timezone.utc).date() - parsed).days
    if age_days <= 30:
        return 1.0
    if age_days <= 180:
        return 0.8
    if age_days <= 365:
        return 0.65
    if document_type in {"regulation", "curriculum", "program", "leadership"}:
        return 0.55
    return 0.4


def authority_score(source_url: str) -> float:
    parsed = urlparse(source_url)
    if parsed.scheme == "file":
        return 0.85
    if parsed.hostname == "hus.vnu.edu.vn":
        return 0.95
    if parsed.hostname == "tuyensinh.hus.vnu.edu.vn":
        return 0.90
    if parsed.hostname and parsed.hostname.endswith(".vnu.edu.vn"):
        return 0.75
    return 0.5


def stable_chunk_id(
    document_id: str,
    source_path: str,
    source_url: str,
    chunk_index: int,
    content_hash: str,
) -> str:
    digest = sha256_bytes(
        "|".join(
            [
                document_id,
                source_path,
                source_url,
                str(chunk_index),
                content_hash,
            ]
        ).encode("utf-8")
    )
    return f"chunk_{digest[:20]}"


def build_summary(
    documents: list[dict],
    chunks: list[DocumentChunkRecord],
    skipped: int,
) -> dict:
    keyword_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    total_length = 0
    total_quality = 0.0
    total_boilerplate = 0.0

    for chunk in chunks:
        type_counter[chunk.document_type] += 1
        total_length += int(chunk.features["text_length"])
        total_quality += float(chunk.features.get("content_quality_score") or 0.0)
        total_boilerplate += float(chunk.features.get("boilerplate_score") or 0.0)
        keyword_counter.update(chunk.features["keyword_hints"])
        hostname = urlparse(chunk.source_url).hostname or "local_or_unknown"
        domain_counter[hostname] += 1

    return {
        "total_documents": len(documents),
        "total_chunks": len(chunks),
        "chunks_by_document_type": dict(type_counter),
        "top_keywords": dict(keyword_counter.most_common(15)),
        "top_domains": dict(domain_counter.most_common(10)),
        "average_chunk_length": round(total_length / len(chunks), 2) if chunks else 0.0,
        "average_content_quality_score": round(total_quality / len(chunks), 4) if chunks else 0.0,
        "average_boilerplate_score": round(total_boilerplate / len(chunks), 4) if chunks else 0.0,
        "empty_or_skipped_count": skipped,
    }


def latest_processed_documents_path(data_root: Path) -> Path:
    documents_root = data_root / "processed" / "documents"
    candidates = sorted(documents_root.glob("*/processed_documents.jsonl"))
    if not candidates:
        raise FileNotFoundError(f"No processed document files found under {documents_root}")
    return candidates[-1]

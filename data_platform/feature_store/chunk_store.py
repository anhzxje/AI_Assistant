"""JSONL storage for generated document chunks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DocumentChunkRecord:
    chunk_id: str
    document_id: str
    source_url: str
    source_path: str
    title: str | None
    document_type: str
    chunk_index: int
    text: str
    character_start: int
    character_end: int
    content_hash: str
    chunk_text_full: str
    preview_text: str
    section_heading: str | None
    context_before: str
    context_after: str
    features: dict[str, Any]
    metadata: dict[str, Any]


class JsonlChunkStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_all(self, records: list[DocumentChunkRecord]) -> None:
        with self.path.open("w", encoding="utf-8", newline="\n") as file_obj:
            for record in records:
                file_obj.write(json.dumps(asdict(record), ensure_ascii=False))
                file_obj.write("\n")

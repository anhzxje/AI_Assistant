"""Append-only crawl manifest writer."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CrawlManifestRecord:
    url: str
    crawl_time: str
    status: str
    depth: int
    parent_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    title: str | None = None
    saved_path: str | None = None
    content_hash: str | None = None
    error: str | None = None
    source: str = "seed_crawler"

    def to_json_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


class JsonlManifestWriter:
    """Simple JSONL writer for crawl events.

    JSONL keeps the manifest append-friendly and robust if a crawl is interrupted.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: CrawlManifestRecord) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as file_obj:
            file_obj.write(json.dumps(record.to_json_dict(), ensure_ascii=False))
            file_obj.write("\n")

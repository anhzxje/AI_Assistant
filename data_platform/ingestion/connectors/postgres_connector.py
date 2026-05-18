"""PostgreSQL ingestion connector for metadata/reporting tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from data_platform.config import get_settings
from data_platform.governance.hashing import sha256_bytes


@dataclass(frozen=True)
class PostgresIngestionResult:
    query_name: str
    raw_path: Path
    row_count: int
    content_hash: str


class PostgresConnector:
    """Run read-only SELECT queries and land rows as raw JSONL snapshots."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn
        self.raw_root = get_settings().resolved_data_root / "raw" / "postgres"

    def export_query(self, query_name: str, sql: str, *, params: tuple[Any, ...] = ()) -> PostgresIngestionResult:
        if not sql.strip().lower().startswith("select"):
            raise ValueError("PostgresConnector only allows read-only SELECT statements.")
        rows = self._execute(sql, params)
        payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows).encode("utf-8")
        digest = sha256_bytes(payload)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_dir = self.raw_root / day
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{safe_name(query_name)}_{digest[:12]}.jsonl"
        if not output_path.exists():
            output_path.write_bytes(payload + (b"\n" if payload else b""))
        return PostgresIngestionResult(query_name=query_name, raw_path=output_path, row_count=len(rows), content_hash=digest)

    def _execute(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        try:
            import psycopg  # type: ignore
        except Exception as exc:  # noqa: BLE001 - dependency is optional for local MVP.
            raise RuntimeError("psycopg is not installed; database ingestion is available when the optional driver is installed.") from exc
        if not self.dsn:
            raise RuntimeError("A PostgreSQL DSN is required for database ingestion.")
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                columns = [desc.name for desc in cur.description or []]
                return [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.lower()).strip("_") or "query"

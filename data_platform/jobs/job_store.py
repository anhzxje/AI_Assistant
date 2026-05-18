"""JSONL-backed local job store."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from data_platform.config import get_settings
from data_platform.jobs.job_schema import JobRecord, JobSource, JobStatus, JobType


class JobStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_settings().resolved_data_root / "jobs" / "jobs.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_job(
        self,
        *,
        job_type: JobType,
        source: JobSource = "manual",
        source_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> JobRecord:
        record = JobRecord(
            job_id=str(uuid4()),
            job_type=job_type,
            status="pending",
            source=source,
            source_id=source_id,
            payload=payload or {},
            created_at=datetime.now(timezone.utc),
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")
        return record

    def list_jobs(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> list[JobRecord]:
        records = self._read_all()
        filtered = []
        for record in records:
            if status and record.status != status:
                continue
            if job_type and record.job_type != job_type:
                continue
            if source and record.source != source:
                continue
            filtered.append(record)
        filtered.sort(key=lambda item: item.created_at, reverse=True)
        return filtered[:limit]

    def get_job(self, job_id: str) -> JobRecord | None:
        for record in self._read_all():
            if record.job_id == job_id:
                return record
        return None

    def get_pending_jobs(self, *, limit: int = 10) -> list[JobRecord]:
        records = [record for record in self._read_all() if record.status == "pending"]
        records.sort(key=lambda item: item.created_at)
        return records[:limit]

    def update_job_status(
        self,
        *,
        job_id: str,
        status: JobStatus,
        error: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> JobRecord | None:
        records = self._read_all()
        updated: JobRecord | None = None
        next_records: list[JobRecord] = []
        now = datetime.now(timezone.utc)
        for record in records:
            if record.job_id == job_id:
                data = record.model_dump()
                data["status"] = status
                if status == "running":
                    data["started_at"] = now
                    data["finished_at"] = None
                    data["error"] = None
                elif status in {"success", "failed", "skipped"}:
                    data["finished_at"] = now
                if error is not None:
                    data["error"] = error
                if result is not None:
                    data["result"] = result
                record = JobRecord.model_validate(data)
                updated = record
            next_records.append(record)
        if updated is None:
            return None
        self._write_all(next_records)
        return updated

    def retry_job(self, *, job_id: str) -> JobRecord | None:
        record = self.get_job(job_id)
        if record is None:
            return None
        return self.update_job_status(job_id=job_id, status="pending", error="", result={})

    def _read_all(self) -> list[JobRecord]:
        if not self.path.exists():
            return []
        records: list[JobRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(JobRecord.model_validate_json(line))
            except Exception:
                continue
        return records

    def _write_all(self, records: list[JobRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n")

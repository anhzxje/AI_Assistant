"""Local executable job runner for admin-triggered maintenance jobs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse

from data_platform.config import get_settings
from data_platform.jobs.job_schema import JobRecord
from data_platform.jobs.job_store import JobStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class JobRunner:
    def __init__(self, store: JobStore | None = None) -> None:
        self.store = store or JobStore()
        self.settings = get_settings()

    def run_next(self, *, dry_run: bool = False) -> JobRecord | None:
        pending = self.store.get_pending_jobs(limit=1)
        if not pending:
            return None
        return self.run_job(pending[0], dry_run=dry_run)

    def run_all(self, *, dry_run: bool = False, max_jobs: int = 20) -> list[JobRecord]:
        completed: list[JobRecord] = []
        for job in self.store.get_pending_jobs(limit=max_jobs):
            completed_job = self.run_job(job, dry_run=dry_run)
            if completed_job is not None:
                completed.append(completed_job)
        return completed

    def run_job(self, job: JobRecord, *, dry_run: bool = False) -> JobRecord:
        self.store.update_job_status(job_id=job.job_id, status="running")
        try:
            if dry_run:
                result = {"dry_run": True, "planned": planned_command(job)}
                updated = self.store.update_job_status(job_id=job.job_id, status="skipped", result=result)
                return updated or job

            if job.job_type == "reindex":
                result = run_command(
                    [
                        sys.executable,
                        "scripts/run_index_qdrant.py",
                        "--latest",
                        "--collection",
                        self.settings.qdrant_collection,
                        "--batch-size",
                        "32",
                        "--recreate",
                    ]
                )
            elif job.job_type == "rebuild_features":
                result = run_command(
                    [
                        sys.executable,
                        "scripts/run_build_features.py",
                        "--latest",
                        "--chunk-size",
                        "800",
                        "--chunk-overlap",
                        "120",
                    ]
                )
            elif job.job_type == "qa_eval":
                result = run_many(
                    [
                        [sys.executable, "scripts/run_data_quality.py"],
                        [sys.executable, "scripts/run_retrieval_eval.py"],
                        [sys.executable, "scripts/run_rag_eval.py"],
                        [sys.executable, "scripts/run_feedback_eval.py"],
                    ]
                )
            elif job.job_type == "recrawl":
                result = self.run_recrawl(job)
            else:
                result = {"skipped": True, "reason": f"Unsupported job type: {job.job_type}"}
                updated = self.store.update_job_status(job_id=job.job_id, status="skipped", result=result)
                return updated or job

            updated = self.store.update_job_status(job_id=job.job_id, status="success", result=result)
            return updated or job
        except Exception as exc:  # noqa: BLE001 - job errors must be captured for admin review.
            result = getattr(exc, "result", {"job_type": job.job_type})
            updated = self.store.update_job_status(
                job_id=job.job_id,
                status="failed",
                error=str(exc),
                result=result,
            )
            return updated or job

    def run_recrawl(self, job: JobRecord) -> dict[str, Any]:
        source_url = str(job.payload.get("source_url") or "").strip()
        request_path = self.settings.resolved_data_root / "metadata" / "recrawl_requests.jsonl"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request = {
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "job_id": job.job_id,
            "source": job.source,
            "source_id": job.source_id,
            "source_url": source_url,
            "payload": job.payload,
        }
        with request_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(request, ensure_ascii=False) + "\n")

        if not source_url:
            return {"skipped": True, "reason": "No source_url in payload", "request_path": str(request_path)}
        if not is_allowed_source(source_url, self.settings.allowed_domains):
            return {
                "skipped": True,
                "reason": "source_url is not in allowed domains",
                "source_url": source_url,
                "request_path": str(request_path),
            }

        seed_path = self.settings.resolved_data_root / "jobs" / f"recrawl_seed_{job.job_id}.txt"
        seed_path.parent.mkdir(parents=True, exist_ok=True)
        seed_path.write_text(source_url + "\n", encoding="utf-8")
        result = run_command(
            [
                sys.executable,
                "scripts/run_seed_crawl.py",
                "--depth",
                "1",
                "--max-pages",
                "10",
                "--seed-file",
                str(seed_path),
            ]
        )
        result["request_path"] = str(request_path)
        result["seed_path"] = str(seed_path)
        return result


def is_allowed_source(source_url: str, allowed_domains: tuple[str, ...]) -> bool:
    parsed = urlparse(source_url)
    host = parsed.netloc.lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


def run_command(command: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("TRANSFORMERS_OFFLINE", "1")
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    result = {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }
    if completed.returncode != 0:
        raise CommandExecutionError(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}",
            result=result,
        )
    return result


def run_many(commands: list[list[str]]) -> dict[str, Any]:
    results = []
    for command in commands:
        results.append(run_command(command))
    return {"commands": results}


def planned_command(job: JobRecord) -> list[str] | list[list[str]]:
    if job.job_type == "reindex":
        return ["python", "scripts/run_index_qdrant.py", "--latest", "--collection", "omni_hus_chunks", "--batch-size", "32", "--recreate"]
    if job.job_type == "rebuild_features":
        return ["python", "scripts/run_build_features.py", "--latest", "--chunk-size", "800", "--chunk-overlap", "120"]
    if job.job_type == "qa_eval":
        return [
            ["python", "scripts/run_data_quality.py"],
            ["python", "scripts/run_retrieval_eval.py"],
            ["python", "scripts/run_rag_eval.py"],
            ["python", "scripts/run_feedback_eval.py"],
        ]
    if job.job_type == "recrawl":
        return ["python", "scripts/run_seed_crawl.py", "--depth", "1", "--max-pages", "10", "--seed-file", "<generated>"]
    return []


class CommandExecutionError(RuntimeError):
    def __init__(self, message: str, *, result: dict[str, Any]) -> None:
        super().__init__(message)
        self.result = result

"""Admin APIs for local executable maintenance jobs."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.services.auth.auth_service import require_admin_user
from data_platform.jobs.job_runner import JobRunner
from data_platform.jobs.job_schema import JobListResponse, JobRecord, JobRunResponse
from data_platform.jobs.job_store import JobStore

router = APIRouter(prefix="/api/admin/jobs", tags=["jobs"], dependencies=[Depends(require_admin_user)])


@router.get("", response_model=JobListResponse)
def list_jobs(
    status: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> JobListResponse:
    jobs = get_job_store().list_jobs(status=status, job_type=job_type, source=source, limit=limit)
    return JobListResponse(count=len(jobs), jobs=jobs)


@router.post("/run-next", response_model=JobRunResponse)
def run_next_job(dry_run: bool = Query(default=False)) -> JobRunResponse:
    job = JobRunner(get_job_store()).run_next(dry_run=dry_run)
    if job is None:
        return JobRunResponse(ran=0, jobs=[], message="No pending jobs.")
    return JobRunResponse(ran=1, jobs=[job], message=f"Ran job {job.job_id}.")


@router.post("/run-all", response_model=JobRunResponse)
def run_all_jobs(
    dry_run: bool = Query(default=False),
    max_jobs: int = Query(default=20, ge=1, le=100),
) -> JobRunResponse:
    jobs = JobRunner(get_job_store()).run_all(dry_run=dry_run, max_jobs=max_jobs)
    return JobRunResponse(ran=len(jobs), jobs=jobs, message=f"Ran {len(jobs)} job(s).")


@router.post("/{job_id}/retry", response_model=JobRecord)
def retry_job(job_id: str) -> JobRecord:
    job = get_job_store().retry_job(job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@lru_cache(maxsize=1)
def get_job_store() -> JobStore:
    return JobStore()

"""Run local admin maintenance jobs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_platform.jobs.job_runner import JobRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pending OmniAssistant admin jobs.")
    parser.add_argument("--run-next", action="store_true", help="Run the oldest pending job.")
    parser.add_argument("--run-all", action="store_true", help="Run pending jobs in FIFO order.")
    parser.add_argument("--dry-run", action="store_true", help="Mark planned jobs as skipped without executing commands.")
    parser.add_argument("--max-jobs", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    runner = JobRunner()
    if args.run_all:
        jobs = runner.run_all(dry_run=args.dry_run, max_jobs=args.max_jobs)
        print(f"jobs_run={len(jobs)}")
        print(json.dumps([job.model_dump(mode="json") for job in jobs], ensure_ascii=False, indent=2))
        return
    if args.run_next:
        job = runner.run_next(dry_run=args.dry_run)
        if job is None:
            print("jobs_run=0")
            print("No pending jobs.")
        else:
            print("jobs_run=1")
            print(json.dumps(job.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return
    raise SystemExit("Pass --run-next or --run-all")


if __name__ == "__main__":
    main()

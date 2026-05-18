"use client";

import { Play, RefreshCw, RotateCcw, StepForward } from "lucide-react";
import type { JobRecord } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

type JobsPanelProps = {
  jobs: JobRecord[];
  message?: string | null;
  onRefresh: () => void;
  onRunNext: () => void;
  onRunAll: () => void;
  onRetry: (jobId: string) => void;
};

export function JobsPanel({ jobs, message, onRefresh, onRunNext, onRunAll, onRetry }: JobsPanelProps) {
  return (
    <section className="rounded-lg border border-line bg-white">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line p-4">
        <div>
          <h2 className="text-base font-semibold text-ink">Jobs</h2>
          <p className="mt-1 text-sm text-slate-500">Executable local maintenance jobs created by admin actions.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onRunNext}
            className="focus-ring inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <StepForward className="h-4 w-4" />
            Run next
          </button>
          <button
            type="button"
            onClick={onRunAll}
            className="focus-ring inline-flex items-center gap-2 rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-cyan-800"
          >
            <Play className="h-4 w-4" />
            Run all
          </button>
          <button
            type="button"
            onClick={onRefresh}
            className="focus-ring inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>
      {message ? <div className="border-b border-line bg-panel px-4 py-2 text-sm text-slate-600">{message}</div> : null}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="border-b border-line bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Job</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Result</th>
              <th className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {jobs.map((job) => (
              <tr key={job.job_id}>
                <td className="px-4 py-3">
                  <div className="font-medium text-ink">{job.job_type}</div>
                  <div className="mt-1 font-mono text-xs text-slate-500">{job.job_id.slice(0, 8)}</div>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge value={job.status} />
                </td>
                <td className="px-4 py-3 text-slate-700">
                  <div>{job.source}</div>
                  {job.source_id ? <div className="mt-1 font-mono text-xs text-slate-400">{job.source_id.slice(0, 8)}</div> : null}
                </td>
                <td className="px-4 py-3 text-slate-700">{formatDate(job.created_at)}</td>
                <td className="max-w-[260px] px-4 py-3 text-slate-600">
                  <div className="line-clamp-2">{job.error || summarizeResult(job.result) || "No result yet"}</div>
                </td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onRetry(job.job_id)}
                    className="focus-ring inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Retry
                  </button>
                </td>
              </tr>
            ))}
            {!jobs.length ? (
              <tr>
                <td className="px-4 py-5 text-slate-500" colSpan={6}>
                  No jobs found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function summarizeResult(result: Record<string, any>) {
  if (!result || !Object.keys(result).length) return "";
  if (result.message) return String(result.message);
  if (result.dry_run) return "Dry run completed";
  return Object.keys(result).slice(0, 3).join(", ");
}

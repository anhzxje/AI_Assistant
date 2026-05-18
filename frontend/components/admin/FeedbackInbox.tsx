"use client";

import { Check, FilePlus2, RefreshCw, RotateCcw, Search, ServerCog } from "lucide-react";
import type { FeedbackRecord, FeedbackSummary } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

type FeedbackFilters = {
  status: string;
  reason: string;
  severity: string;
  intent: string;
};

type FeedbackInboxProps = {
  feedback: FeedbackRecord[];
  summary: FeedbackSummary | null;
  filters: FeedbackFilters;
  onFiltersChange: (filters: FeedbackFilters) => void;
  onRefresh: () => void;
  onAction: (feedbackId: string, action: "reviewed" | "eval" | "reindex" | "recrawl") => void;
  message?: string | null;
  compact?: boolean;
};

export function FeedbackInbox({
  feedback,
  summary,
  filters,
  onFiltersChange,
  onRefresh,
  onAction,
  message,
  compact
}: FeedbackInboxProps) {
  return (
    <section className="rounded-lg border border-line bg-white">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line p-4">
        <div>
          <h2 className="text-base font-semibold text-ink">Feedback Inbox</h2>
          <p className="mt-1 text-sm text-slate-500">Prioritize answer quality issues and turn them into evals or jobs.</p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="focus-ring inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      <div className="border-b border-line p-3">
        <div className="flex flex-wrap gap-2">
          <Select label="Status" value={filters.status} onChange={(status) => onFiltersChange({ ...filters, status })} options={statusOptions} />
          <Select label="Reason" value={filters.reason} onChange={(reason) => onFiltersChange({ ...filters, reason })} options={reasonOptions} />
          <Select label="Severity" value={filters.severity} onChange={(severity) => onFiltersChange({ ...filters, severity })} options={severityOptions} />
          <Select label="Intent" value={filters.intent} onChange={(intent) => onFiltersChange({ ...filters, intent })} options={intentOptions} />
        </div>
        {summary ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-4">
            <MiniMetric label="Total" value={summary.total} />
            <MiniMetric label="New" value={summary.by_status.new ?? 0} />
            <MiniMetric label="High severity" value={summary.by_severity.high ?? 0} />
            <MiniMetric label="Missing source" value={summary.by_reason.missing_source ?? 0} />
          </div>
        ) : null}
        {message ? <div className="mt-3 text-sm text-slate-600">{message}</div> : null}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1060px] text-left text-sm">
          <thead className="border-b border-line bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Feedback</th>
              <th className="px-4 py-3">Issue</th>
              <th className="px-4 py-3">Query</th>
              {!compact ? <th className="px-4 py-3">Diagnostics</th> : null}
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {feedback.map((item) => (
              <tr key={item.feedback_id}>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge value={item.rating} />
                    <StatusBadge value={item.status} />
                  </div>
                  <div className="mt-2 text-xs text-slate-500">{formatDate(item.created_at)}</div>
                  <div className="mt-1 font-mono text-xs text-slate-400">{item.feedback_id.slice(0, 8)}</div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge value={item.severity} />
                    <span className="font-medium text-slate-700">{item.reason}</span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{item.intent || "unknown intent"}</div>
                </td>
                <td className="max-w-[360px] px-4 py-3 text-slate-700">
                  <div className="line-clamp-2">{item.query || "(no query)"}</div>
                  {item.correction ? <div className="mt-2 rounded-md bg-panel p-2 text-xs text-slate-600">Correction: {item.correction}</div> : null}
                </td>
                {!compact ? (
                  <td className="px-4 py-3 text-slate-600">
                    <div>{item.diagnostics?.suspected_issue || "no diagnostic"}</div>
                    <div className="mt-1 text-xs text-slate-500">{item.diagnostics?.source_count ?? 0} sources</div>
                  </td>
                ) : null}
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <ActionButton label="Reviewed" icon={Check} onClick={() => onAction(item.feedback_id, "reviewed")} />
                    <ActionButton label="Eval" icon={FilePlus2} onClick={() => onAction(item.feedback_id, "eval")} />
                    <ActionButton label="Reindex" icon={ServerCog} onClick={() => onAction(item.feedback_id, "reindex")} />
                    <ActionButton label="Recrawl" icon={Search} onClick={() => onAction(item.feedback_id, "recrawl")} />
                  </div>
                </td>
              </tr>
            ))}
            {!feedback.length ? (
              <tr>
                <td className="px-4 py-5 text-slate-500" colSpan={compact ? 4 : 5}>
                  No feedback found for the current filters.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Select({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="min-w-[160px]">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="focus-ring w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-slate-700"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-line bg-panel p-3">
      <div className="text-xs uppercase tracking-normal text-slate-500">{label}</div>
      <div className="mt-1 text-lg font-semibold text-ink">{value}</div>
    </div>
  );
}

function ActionButton({ label, icon: Icon, onClick }: { label: string; icon: typeof RotateCcw; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="focus-ring inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

const statusOptions = [
  { label: "All status", value: "all" },
  { label: "New", value: "new" },
  { label: "Reviewed", value: "reviewed" },
  { label: "Promoted", value: "promoted_to_eval" },
  { label: "Queued reindex", value: "queued_for_reindex" },
  { label: "Queued recrawl", value: "queued_for_recrawl" },
  { label: "Ignored", value: "ignored" }
];

const reasonOptions = [
  { label: "All reasons", value: "all" },
  { label: "Wrong answer", value: "wrong_answer" },
  { label: "Missing source", value: "missing_source" },
  { label: "Outdated data", value: "outdated_data" },
  { label: "Irrelevant retrieval", value: "irrelevant_retrieval" },
  { label: "Bad citation", value: "bad_citation" },
  { label: "Too slow", value: "too_slow" },
  { label: "Other", value: "other" }
];

const severityOptions = [
  { label: "All severity", value: "all" },
  { label: "High", value: "high" },
  { label: "Medium", value: "medium" },
  { label: "Low", value: "low" }
];

const intentOptions = [
  { label: "All intents", value: "all" },
  { label: "Institutional RAG", value: "institutional_rag" },
  { label: "General chat", value: "general_chat" },
  { label: "Daily briefing", value: "daily_briefing" },
  { label: "Clarification", value: "clarification" },
  { label: "Fallback", value: "fallback" }
];

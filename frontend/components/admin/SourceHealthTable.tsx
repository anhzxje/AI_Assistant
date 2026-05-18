"use client";

import { ExternalLink } from "lucide-react";
import type { SourceHealth } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

type SourceHealthTableProps = {
  sources: SourceHealth[];
  activeDomain?: string;
  onDomainSelect?: (domain: string) => void;
};

export function SourceHealthTable({ sources, activeDomain = "all", onDomainSelect }: SourceHealthTableProps) {
  return (
    <section className="rounded-lg border border-line bg-white">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line p-4">
        <div>
          <h2 className="text-base font-semibold text-ink">Source Health</h2>
          <p className="mt-1 text-sm text-slate-500">Domain coverage, freshness, duplicate signals, and authority scores.</p>
        </div>
        {activeDomain !== "all" ? <StatusBadge value={`filtered: ${activeDomain}`} tone="info" /> : null}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="border-b border-line bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Domain</th>
              <th className="px-4 py-3">Docs</th>
              <th className="px-4 py-3">Chunks</th>
              <th className="px-4 py-3">Freshness</th>
              <th className="px-4 py-3">Authority</th>
              <th className="px-4 py-3">Issues</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {sources.map((source) => (
              <tr key={source.domain} className={activeDomain === source.domain ? "bg-cyan-50/60" : "bg-white"}>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onDomainSelect?.(source.domain)}
                    className="focus-ring inline-flex max-w-[260px] items-center gap-2 rounded-md px-2 py-1 text-left font-medium text-brand hover:bg-slate-100"
                  >
                    <span className="truncate">{source.domain}</span>
                    <ExternalLink className="h-3 w-3 shrink-0" />
                  </button>
                  <div className="mt-1 text-xs text-slate-500">{formatTypes(source.document_types)}</div>
                </td>
                <td className="px-4 py-3 tabular-nums text-slate-700">{source.document_count}</td>
                <td className="px-4 py-3 tabular-nums text-slate-700">{source.chunk_count}</td>
                <td className="px-4 py-3">
                  <ScoreBar value={source.average_freshness_score} />
                </td>
                <td className="px-4 py-3">
                  <ScoreBar value={source.average_authority_score} />
                </td>
                <td className="px-4 py-3 text-slate-700">
                  <div>{source.stale_or_unknown_documents} stale</div>
                  <div className="text-xs text-slate-500">{source.duplicate_content_hashes} duplicate hashes</div>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge value={source.status} />
                </td>
              </tr>
            ))}
            {!sources.length ? (
              <tr>
                <td className="px-4 py-5 text-slate-500" colSpan={7}>
                  No source health data found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ScoreBar({ value }: { value: number }) {
  const bounded = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
  return (
    <div className="w-36 max-w-full">
      <div className="h-2 rounded-full bg-slate-100">
        <div className="h-2 rounded-full bg-accent" style={{ width: `${Math.round(bounded * 100)}%` }} />
      </div>
      <div className="mt-1 text-xs tabular-nums text-slate-500">{Math.round(bounded * 100)}%</div>
    </div>
  );
}

function formatTypes(types: Record<string, number>) {
  const items = Object.entries(types)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  if (!items.length) return "No document types";
  return items.map(([type, count]) => `${type}: ${count}`).join(", ");
}

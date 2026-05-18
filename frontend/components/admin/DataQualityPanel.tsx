"use client";

import { AlertCircle, Database, FileWarning } from "lucide-react";
import type { AdminSystemSummary } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

type DataQualityPanelProps = {
  summary: AdminSystemSummary | null;
};

export function DataQualityPanel({ summary }: DataQualityPanelProps) {
  const data = summary?.data;
  const quality = summary?.qa.data_quality;
  const chunkIssues = quality?.chunks?.issue_count ?? 0;
  const duplicateChunkIds = quality?.chunks?.duplicate_chunk_id_count ?? 0;
  const documentIssues = quality?.processed_documents?.issue_count ?? 0;
  const staleDocs = data?.stale_or_unknown_date_count ?? quality?.processed_documents?.stale_or_unknown_date_count ?? 0;
  const duplicateDocs = data?.duplicate_content_hash_count ?? quality?.processed_documents?.duplicate_content_hash_count ?? 0;

  return (
    <section className="rounded-lg border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <Database className="mt-0.5 h-5 w-5 text-brand" />
        <div>
          <h2 className="text-base font-semibold text-ink">Data Quality</h2>
          <p className="mt-1 text-sm text-slate-500">Signals that affect retrieval quality and source trust.</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <QualityTile label="Chunk issues" value={chunkIssues} ok={chunkIssues === 0} />
        <QualityTile label="Duplicate chunk IDs" value={duplicateChunkIds} ok={duplicateChunkIds === 0} />
        <QualityTile label="Document issues" value={documentIssues} ok={documentIssues === 0} />
        <QualityTile label="Stale or undated docs" value={staleDocs} ok={staleDocs === 0} />
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border border-line bg-panel p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-ink">
            <FileWarning className="h-4 w-4 text-amber-600" />
            Missing knowledge indicators
          </div>
          <div className="mt-3 space-y-2">
            {(data?.missing_knowledge_indicators ?? []).map((indicator) => (
              <div key={indicator.label} className="flex items-start justify-between gap-3 rounded-md bg-white p-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-slate-700">{indicator.label}</div>
                  <div className="mt-1 text-xs text-slate-500">{indicator.action}</div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="text-sm font-semibold tabular-nums text-ink">{indicator.count}</span>
                  <StatusBadge value={indicator.severity} />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-md border border-line bg-panel p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-ink">
            <AlertCircle className="h-4 w-4 text-red-600" />
            Source hygiene
          </div>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <StatusLine label="Duplicate document hashes" value={duplicateDocs} ok={duplicateDocs === 0} />
            <StatusLine label="Empty or skipped records" value={data?.empty_or_skipped_count ?? 0} ok={(data?.empty_or_skipped_count ?? 0) === 0} />
            <StatusLine label="Unknown type chunks" value={data?.unknown_chunk_count ?? 0} ok={(data?.unknown_chunk_count ?? 0) === 0} />
            <StatusLine
              label="Qdrant points vs chunks"
              value={`${data?.qdrant_points ?? 0} / ${data?.total_chunks ?? 0}`}
              ok={(data?.qdrant_points ?? 0) === (data?.total_chunks ?? 0)}
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function QualityTile({ label, value, ok }: { label: string; value: number; ok: boolean }) {
  return (
    <div className={ok ? "rounded-md border border-emerald-200 bg-emerald-50 p-3" : "rounded-md border border-amber-200 bg-amber-50 p-3"}>
      <div className="text-xs font-medium uppercase tracking-normal text-slate-500">{label}</div>
      <div className={ok ? "mt-2 text-xl font-semibold text-emerald-700" : "mt-2 text-xl font-semibold text-amber-700"}>{value}</div>
    </div>
  );
}

function StatusLine({ label, value, ok }: { label: string; value: string | number; ok: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-white px-3 py-2">
      <span>{label}</span>
      <span className={ok ? "font-semibold text-emerald-700" : "font-semibold text-amber-700"}>{value}</span>
    </div>
  );
}

"use client";

import { ExternalLink, FileText, X } from "lucide-react";
import type { AdminDocumentDetail } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

type DocumentDetailDrawerProps = {
  detail: AdminDocumentDetail | null;
  loading?: boolean;
  onClose: () => void;
};

export function DocumentDetailDrawer({ detail, loading, onClose }: DocumentDetailDrawerProps) {
  if (!detail && !loading) return null;
  const document = detail?.document;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/35">
      <div className="absolute inset-y-0 right-0 flex w-full max-w-3xl flex-col border-l border-line bg-white shadow-xl">
        <div className="flex items-start justify-between gap-3 border-b border-line px-4 py-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm font-semibold text-ink">
              <FileText className="h-4 w-4 text-brand" />
              Document detail
            </div>
            <div className="mt-1 truncate text-sm text-slate-500">{document?.document_id ?? "Loading..."}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="focus-ring rounded-md border border-line p-2 text-slate-600 hover:bg-slate-50"
            aria-label="Close document detail"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading ? (
          <div className="p-4 text-sm text-slate-500">Loading document detail...</div>
        ) : document ? (
          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            <div className="rounded-lg border border-line bg-panel p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-ink">{document.title ?? "Untitled"}</h2>
                  <p className="mt-2 text-sm text-slate-600">{document.text_preview || "No text preview available."}</p>
                </div>
                <StatusBadge value={document.document_type} />
              </div>
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <DetailLine label="Domain" value={document.domain ?? domainFromUrl(document.source_url)} />
                <DetailLine label="Language" value={document.language || "unknown"} />
                <DetailLine label="Published" value={document.published_date || "unknown"} />
                <DetailLine label="Characters" value={document.text_length.toLocaleString()} />
                <DetailLine label="Content hash" value={(document.content_hash || "").slice(0, 24)} mono />
                <DetailLine label="Chunks" value={detail.chunk_count} />
              </div>
              {document.source_url ? (
                <a
                  href={document.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="focus-ring mt-4 inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-brand hover:bg-slate-50"
                >
                  Open source URL
                  <ExternalLink className="h-4 w-4" />
                </a>
              ) : null}
            </div>

            <section className="mt-4 rounded-lg border border-line bg-white">
              <div className="border-b border-line px-4 py-3">
                <h3 className="text-sm font-semibold text-ink">Chunk Preview</h3>
              </div>
              <div className="divide-y divide-line">
                {detail.chunks.map((chunk) => (
                  <article key={chunk.chunk_id} className="p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="font-mono text-xs text-slate-500">{chunk.chunk_id}</div>
                      <div className="flex gap-2">
                        <StatusBadge value={`fresh ${Math.round((chunk.freshness_score ?? 0) * 100)}%`} tone="info" />
                        <StatusBadge value={`auth ${Math.round((chunk.authority_score ?? 0) * 100)}%`} tone="neutral" />
                      </div>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{chunk.preview || chunk.text}</p>
                  </article>
                ))}
                {!detail.chunks.length ? <div className="p-4 text-sm text-slate-500">No chunks linked to this document.</div> : null}
              </div>
            </section>
          </div>
        ) : (
          <div className="p-4 text-sm text-red-600">Document detail could not be loaded.</div>
        )}
      </div>
    </div>
  );
}

function DetailLine({ label, value, mono }: { label: string; value: string | number; mono?: boolean }) {
  return (
    <div className="rounded-md bg-white p-3">
      <div className="text-xs uppercase tracking-normal text-slate-500">{label}</div>
      <div className={mono ? "mt-1 break-all font-mono text-xs text-slate-700" : "mt-1 text-sm font-medium text-slate-700"}>{value}</div>
    </div>
  );
}

function domainFromUrl(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "unknown";
  }
}

"use client";

import { ExternalLink, FileText } from "lucide-react";
import type { AdminDocument } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

type DocumentTableProps = {
  documents: AdminDocument[];
  total: number;
  activeDocumentId?: string | null;
  onOpenDetail: (document: AdminDocument) => void;
};

export function DocumentTable({ documents, total, activeDocumentId, onOpenDetail }: DocumentTableProps) {
  return (
    <section className="rounded-lg border border-line bg-white">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line p-4">
        <div>
          <h2 className="text-base font-semibold text-ink">Documents</h2>
          <p className="mt-1 text-sm text-slate-500">
            Showing {documents.length} of {total} processed documents.
          </p>
        </div>
        <StatusBadge value={`${sumChars(documents).toLocaleString()} chars`} tone="info" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="border-b border-line bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Domain</th>
              <th className="px-4 py-3">Text</th>
              <th className="px-4 py-3">Hash</th>
              <th className="px-4 py-3">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {documents.map((document) => (
              <tr key={document.document_id} className={document.document_id === activeDocumentId ? "bg-cyan-50/60" : "bg-white"}>
                <td className="max-w-[360px] px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onOpenDetail(document)}
                    className="focus-ring flex max-w-full items-start gap-2 rounded-md px-2 py-1 text-left hover:bg-slate-100"
                  >
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
                    <span className="min-w-0">
                      <span className="block truncate font-medium text-ink">{document.title ?? "Untitled"}</span>
                      <span className="mt-1 block truncate font-mono text-xs text-slate-500">{document.document_id}</span>
                    </span>
                  </button>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge value={document.document_type} tone="neutral" />
                </td>
                <td className="px-4 py-3 text-slate-700">{document.domain ?? domainFromUrl(document.source_url)}</td>
                <td className="px-4 py-3 tabular-nums text-slate-700">{document.text_length.toLocaleString()}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-500">{(document.content_hash || "").slice(0, 16)}</td>
                <td className="px-4 py-3">
                  <a
                    href={document.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="focus-ring inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-brand hover:bg-slate-100"
                  >
                    Open <ExternalLink className="h-3 w-3" />
                  </a>
                </td>
              </tr>
            ))}
            {!documents.length ? (
              <tr>
                <td className="px-4 py-5 text-slate-500" colSpan={6}>
                  No documents match the current filters.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function sumChars(documents: AdminDocument[]) {
  return documents.reduce((sum, item) => sum + item.text_length, 0);
}

function domainFromUrl(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "unknown";
  }
}

"use client";

import { ExternalLink, FileText } from "lucide-react";
import { useState } from "react";
import type { AssistantSource } from "@/lib/api";

export function CitationCard({
  source,
  index,
  compact = false,
  isAdmin = false
}: {
  source: AssistantSource;
  index: number;
  compact?: boolean;
  isAdmin?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const title = source.title ?? source.subject ?? source.summary ?? source.type ?? "Source";
  const type = source.document_type ?? source.type ?? "source";
  const url = source.source_url;
  const usage = source.usage ?? (source.used_in_answer === false ? "retrieval_debug" : "cited");
  const preview = source.snippet ?? source.preview_text ?? source.preview;
  const fullPreview = source.chunk_text_full ?? source.full_text ?? source.preview_text ?? source.preview;
  const displayPreview = expanded || isAdmin ? compactText(fullPreview, isAdmin ? 900 : 520) : compactText(preview, 180);
  const sourceLabel = url ? safeDomain(url) : source.source_mode ?? source.type;
  const canExpand = Boolean(fullPreview && fullPreview.length > displayPreview.length);

  return (
    <article className={`rounded-lg border border-line bg-white ${compact ? "p-2" : "p-3"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-start gap-2">
            <span className="mt-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded bg-slate-100 px-1 text-[11px] font-semibold text-slate-600">
              {index}
            </span>
            <div className="min-w-0">
              <h3 className="break-words text-sm font-semibold leading-5 text-ink">{title}</h3>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span className="inline-flex items-center gap-1">
                  <FileText className="h-3.5 w-3.5" />
                  {type}
                </span>
                {sourceLabel ? <span>{sourceLabel}</span> : null}
                {isAdmin ? (
                  <span className={`rounded-full px-2 py-0.5 ${usage === "cited" ? "bg-teal-50 text-teal-700" : "bg-slate-100 text-slate-600"}`}>
                    {usage}
                  </span>
                ) : null}
                {isAdmin && typeof source.score === "number" ? <span>score {source.score.toFixed(4)}</span> : null}
              </div>
            </div>
          </div>
        </div>
        {url ? (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="focus-ring inline-flex h-8 shrink-0 items-center gap-1 rounded-md px-2 text-xs font-medium text-brand hover:bg-slate-100"
          >
            Source <ExternalLink className="h-3.5 w-3.5" />
          </a>
        ) : null}
      </div>
      {isAdmin && source.relevance_reason ? <p className="mt-2 text-xs leading-5 text-slate-500">{source.relevance_reason}</p> : null}
      {source.section_heading ? <p className="mt-2 text-xs font-medium text-slate-500">{source.section_heading}</p> : null}
      {displayPreview ? <p className={`mt-2 break-words leading-6 text-slate-700 ${compact ? "text-xs" : "text-sm"}`}>{displayPreview}</p> : null}
      {canExpand ? (
        <button type="button" onClick={() => setExpanded((value) => !value)} className="mt-2 text-xs font-medium text-brand hover:underline">
          {expanded ? "Thu gọn" : "Xem thêm"}
        </button>
      ) : null}
    </article>
  );
}

function compactText(value: unknown, limit: number) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  const boundary = text.lastIndexOf(" ", limit);
  return `${text.slice(0, boundary > 80 ? boundary : limit).trim()}...`;
}

function safeDomain(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

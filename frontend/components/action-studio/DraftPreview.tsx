"use client";

import { Copy, Download } from "lucide-react";
import type { ActionDraft } from "@/lib/api";

export function DraftPreview({ draft }: { draft: ActionDraft | null }) {
  async function copy() {
    if (draft) await navigator.clipboard.writeText(draft.content);
  }

  function download() {
    if (!draft) return;
    const blob = new Blob([draft.content], { type: draft.format === "json" ? "application/json" : "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${draft.draft_id}.${draft.format === "json" ? "json" : "md"}`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="rounded-lg border border-line bg-white">
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div>
          <h2 className="text-base font-semibold text-ink">{draft?.title ?? "Preview"}</h2>
          <p className="text-xs text-slate-500">{draft ? `${draft.draft_type} | ${draft.created_at}` : "Chưa có bản nháp."}</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={copy} disabled={!draft} className="focus-ring inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-sm disabled:text-slate-300">
            <Copy className="h-4 w-4" />
            Copy
          </button>
          <button type="button" onClick={download} disabled={!draft} className="focus-ring inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-sm disabled:text-slate-300">
            <Download className="h-4 w-4" />
            Download
          </button>
        </div>
      </div>
      <pre className="max-h-[560px] overflow-auto whitespace-pre-wrap p-4 text-sm leading-6 text-slate-800">{draft?.content ?? "Tạo một bản nháp để xem nội dung ở đây."}</pre>
    </section>
  );
}


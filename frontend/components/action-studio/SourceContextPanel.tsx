"use client";

import type { ActionDraft } from "@/lib/api";

export function SourceContextPanel({ draft }: { draft: ActionDraft | null }) {
  return (
    <aside className="space-y-4">
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Đây là bản nháp. Vui lòng kiểm tra trước khi sử dụng.
      </div>
      <div className="rounded-lg border border-line bg-white p-4">
        <h2 className="text-sm font-semibold text-ink">Nguồn đã dùng</h2>
        <div className="mt-3 space-y-2">
          {draft?.sources?.length ? (
            draft.sources.slice(0, 12).map((source, index) => (
              <div key={`${source.source_type}-${source.source_id}-${index}`} className="rounded-md border border-line p-2 text-xs">
                <div className="font-medium text-slate-800">{source.title ?? source.source_type}</div>
                <div className="mt-1 text-slate-500">{source.source_type}{source.source_id ? `:${source.source_id}` : ""}</div>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">Nguồn sẽ hiện sau khi tạo draft.</p>
          )}
        </div>
      </div>
    </aside>
  );
}


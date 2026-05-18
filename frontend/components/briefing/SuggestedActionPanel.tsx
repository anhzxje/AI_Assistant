"use client";

import type { SmartBriefing } from "@/lib/api";

export function SuggestedActionPanel({ briefing }: { briefing: SmartBriefing | null }) {
  const actions = briefing?.suggested_actions ?? [];
  return (
    <section className="rounded-lg border border-line bg-white p-5">
      <h3 className="text-sm font-semibold text-ink">Suggested Actions</h3>
      <div className="mt-3 space-y-2">
        {actions.map((action, index) => (
          <div key={`${action.source_type ?? "source"}-${action.source_id ?? index}`} className="rounded-md bg-panel p-3 text-sm text-slate-700">
            {action.title}
          </div>
        ))}
        {!actions.length ? <p className="text-sm text-slate-500">Không có hành động gợi ý từ dữ liệu hiện có.</p> : null}
      </div>
    </section>
  );
}

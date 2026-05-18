"use client";

import type { SmartBriefing } from "@/lib/api";

export function PriorityList({ briefing }: { briefing: SmartBriefing | null }) {
  const priorities = briefing?.top_priorities ?? [];
  return (
    <section className="rounded-lg border border-line bg-white p-5">
      <h3 className="text-sm font-semibold text-ink">Top Priorities</h3>
      <div className="mt-3 space-y-2">
        {priorities.map((priority, index) => (
          <div key={priority.priority_id ?? index} className="rounded-md bg-panel p-3">
            <div className="text-sm font-medium text-ink">{priority.title}</div>
            <div className="mt-1 text-xs text-slate-500">
              {priority.reason} · score {Number(priority.score ?? 0).toFixed(1)}
            </div>
          </div>
        ))}
        {!priorities.length ? <p className="text-sm text-slate-500">Không có ưu tiên nổi bật từ dữ liệu đã đồng bộ.</p> : null}
      </div>
    </section>
  );
}

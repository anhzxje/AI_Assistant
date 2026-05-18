"use client";

import Link from "next/link";
import type { KnowledgeSummary } from "@/lib/api";
import { SyncStatsCard } from "./SyncStatsCard";

export function KnowledgeSummaryPanel({ summary }: { summary: KnowledgeSummary | null }) {
  const relatedCount =
    (summary?.node_counts?.EmailThread ?? 0) + (summary?.node_counts?.CalendarEvent ?? 0) + (summary?.node_counts?.Task ?? 0);

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-4">
        <SyncStatsCard label="Người liên quan" value={summary?.node_counts?.Person ?? 0} />
        <SyncStatsCard label="Dự án" value={summary?.node_counts?.Project ?? 0} />
        <SyncStatsCard label="Deadline gấp" value={summary?.node_counts?.Deadline ?? 0} />
        <SyncStatsCard label="Email/lịch/task" value={relatedCount} />
      </div>
      <section className="rounded-lg border border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Ngữ cảnh hôm nay</h2>
            <p className="mt-1 text-sm text-slate-500">
              Đây là phần tóm tắt các quan hệ Lumi tìm thấy từ email, lịch và task hôm nay.
            </p>
          </div>
          <Link href="/knowledge" className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
            Mở sơ đồ tri thức
          </Link>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <List title="Người nổi bật" items={summary?.top_people ?? []} />
          <List title="Dự án liên quan" items={summary?.top_projects ?? []} />
          <List title="Deadline cần chú ý" items={summary?.recent_deadlines ?? []} />
        </div>
      </section>
    </div>
  );
}

function List({ title, items }: { title: string; items: Array<Record<string, any>> }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <div className="mt-2 space-y-2">
        {items.slice(0, 6).map((item, index) => (
          <div key={item.node_id ?? index} className="rounded-md bg-panel p-2 text-sm text-slate-700">
            {item.label}
          </div>
        ))}
        {!items.length ? <p className="text-sm text-slate-500">Chưa có mục nào.</p> : null}
      </div>
    </div>
  );
}

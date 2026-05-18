"use client";

import type { SmartBriefing } from "@/lib/api";

export function SmartReportCard({ briefing }: { briefing: SmartBriefing | null }) {
  return (
    <section className="rounded-lg border border-line bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">{briefing?.headline ?? "Morning Report"}</h2>
          <p className="mt-1 text-xs text-slate-500">{briefing?.generated_at ? `Cập nhật: ${briefing.generated_at}` : "Chưa tạo briefing"}</p>
        </div>
        <span className="rounded-full border border-line bg-panel px-3 py-1 text-xs font-medium text-slate-600">
          {briefing?.metadata?.source_mode === "mock" ? "Dữ liệu mẫu" : briefing?.metadata?.source_mode === "real" ? "Google" : "Chưa kết nối"}
        </span>
      </div>
      <p className="mt-4 text-sm leading-6 text-slate-700">
        {briefing?.morning_report ?? "Tạo briefing để Lumi tổng hợp ưu tiên, email, lịch và task trong ngày."}
      </p>
    </section>
  );
}

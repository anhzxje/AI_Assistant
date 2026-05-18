"use client";

import type { DailyBriefing, GoogleIntegrationStatus, SyncResponse } from "@/lib/api";
import { SyncStatsCard } from "./SyncStatsCard";

export function sourceLabel(mode?: string) {
  if (mode === "real") return "Nguồn: Google";
  if (mode === "mock") return "Nguồn: Dữ liệu mẫu";
  if (mode === "mixed") return "Nguồn: Google + dữ liệu mẫu";
  return "Chưa kết nối";
}

export function BriefingOverview({
  briefing,
  status,
  lastSync
}: {
  briefing: DailyBriefing | null;
  status: GoogleIntegrationStatus | null;
  lastSync: SyncResponse[];
}) {
  const email = briefing?.email_summary;
  const nextEvent = briefing?.today_events?.[0];
  const sourceMode = String(briefing?.metadata?.source_mode ?? "not_connected");

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Overview</h2>
            <p className="mt-1 text-sm text-slate-500">{sourceLabel(sourceMode)}</p>
          </div>
          <span className="rounded-full border border-line bg-panel px-3 py-1 text-xs font-medium text-slate-600">
            {status?.gmail_connected || status?.calendar_connected ? "Google đã kết nối" : "Chưa kết nối Google"}
          </span>
        </div>
        {briefing?.summary ? <p className="mt-4 text-sm leading-6 text-slate-700">{briefing.summary}</p> : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SyncStatsCard label="Email" value={email?.total_messages ?? 0} hint={`${email?.unread_count ?? 0} chưa đọc`} />
        <SyncStatsCard label="Quan trọng" value={email?.important_count ?? 0} hint={`${briefing?.ignored_noise_count ?? 0} mục nhiễu đã bỏ qua`} />
        <SyncStatsCard label="Lịch hôm nay" value={briefing?.today_events.length ?? 0} hint={nextEvent?.summary ?? "Không có sự kiện gần nhất"} />
        <SyncStatsCard label="Tasks" value={briefing?.tasks.length ?? 0} hint={`${briefing?.priorities.length ?? 0} ưu tiên`} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-line bg-white p-5">
          <h3 className="text-sm font-semibold text-ink">Ưu tiên</h3>
          <div className="mt-3 space-y-2">
            {(briefing?.priorities ?? []).map((item) => (
              <div key={item} className="rounded-md bg-panel p-3 text-sm text-slate-700">
                {item}
              </div>
            ))}
          </div>
        </section>
        <section className="rounded-lg border border-line bg-white p-5">
          <h3 className="text-sm font-semibold text-ink">Lần đồng bộ gần nhất</h3>
          <div className="mt-3 space-y-2">
            {lastSync.length ? (
              lastSync.map((item, index) => (
                <div key={`${item.mode}-${index}`} className="rounded-md bg-panel p-3 text-sm text-slate-700">
                  {item.records_synced} bản ghi từ {item.source_mode === "mock" ? "dữ liệu mẫu" : "Google"}
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500">Chưa có đồng bộ trong phiên này.</div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

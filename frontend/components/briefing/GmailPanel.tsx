"use client";

import { Loader2, RefreshCw } from "lucide-react";
import type { DailyBriefing } from "@/lib/api";
import { GmailRange, MaxResultsSelector, SyncRangeSelector } from "./SyncRangeSelector";
import { SyncStatsCard } from "./SyncStatsCard";

export function GmailPanel({
  briefing,
  connected,
  range,
  maxResults,
  syncing,
  onRangeChange,
  onMaxResultsChange,
  onSync
}: {
  briefing: DailyBriefing | null;
  connected: boolean;
  range: GmailRange;
  maxResults: number;
  syncing: boolean;
  onRangeChange: (value: GmailRange) => void;
  onMaxResultsChange: (value: number) => void;
  onSync: () => void;
}) {
  const summary = briefing?.email_summary;
  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-line bg-white p-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">Gmail</h2>
            <p className="mt-1 text-sm text-slate-500">Đồng bộ hộp thư ở chế độ chỉ đọc.</p>
          </div>
          <button
            type="button"
            onClick={onSync}
            disabled={syncing || !connected}
            className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-brand px-4 text-sm font-medium text-white hover:bg-cyan-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Đồng bộ Gmail
          </button>
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <SyncRangeSelector label="Khoảng thời gian" value={range} options={["7d", "30d", "90d", "1y", "all_recent"]} onChange={onRangeChange} />
          <MaxResultsSelector value={maxResults} onChange={onMaxResultsChange} />
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SyncStatsCard label="Tổng email" value={summary?.total_messages ?? 0} />
        <SyncStatsCard label="Chưa đọc" value={summary?.unread_count ?? 0} />
        <SyncStatsCard label="Đã đọc" value={summary?.read_count ?? 0} />
        <SyncStatsCard label="Quan trọng" value={summary?.important_count ?? 0} />
      </div>

      <section className="rounded-lg border border-line bg-white p-5">
        <h3 className="text-sm font-semibold text-ink">Email quan trọng</h3>
        <div className="mt-3 space-y-3">
          {(briefing?.important_emails ?? []).map((message, index) => (
            <article key={message.message_id ?? index} className="rounded-md border border-line p-3">
              <div className="text-sm font-semibold text-ink">{message.subject || "(No subject)"}</div>
              <div className="mt-1 text-xs text-slate-500">{message.from} · {message.category ?? "email"}</div>
              <p className="mt-2 text-sm leading-6 text-slate-700">{message.snippet}</p>
            </article>
          ))}
          {!(briefing?.important_emails ?? []).length ? <p className="text-sm text-slate-500">Không có email quan trọng sau khi lọc nhiễu.</p> : null}
        </div>
      </section>
    </div>
  );
}

"use client";

import { AlertCircle, CheckCircle2, Clock, Loader2 } from "lucide-react";
import type { SyncResponse } from "@/lib/api";

function formatMs(value?: number) {
  if (value === undefined || value === null) return "0.0s";
  return `${(value / 1000).toFixed(1)}s`;
}

export function SyncProgressCard({
  title,
  syncing,
  response,
  error,
  elapsedMs
}: {
  title: string;
  syncing: boolean;
  response?: SyncResponse | null;
  error?: string | null;
  elapsedMs?: number;
}) {
  const metadata = response?.metadata ?? {};
  const requested = metadata.date_range
    ? `${metadata.date_range.start_date} - ${metadata.date_range.end_date}`
    : metadata.requested_max ?? metadata.days_ahead ?? "-";
  const fetched = metadata.fetched_count ?? response?.events_count ?? response?.records_synced ?? 0;
  const processed = metadata.processed_count ?? response?.events_count ?? response?.records_synced ?? 0;
  const status = syncing ? "Đang đồng bộ" : error ? "Có lỗi" : response ? "Hoàn tất" : "Chưa chạy";

  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          <p className="mt-1 text-xs text-slate-500">{status}</p>
        </div>
        {syncing ? (
          <Loader2 className="h-5 w-5 animate-spin text-cyan-700" />
        ) : error ? (
          <AlertCircle className="h-5 w-5 text-red-600" />
        ) : response ? (
          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
        ) : (
          <Clock className="h-5 w-5 text-slate-400" />
        )}
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${error ? "bg-red-500" : syncing ? "bg-cyan-600" : response ? "bg-emerald-600" : "bg-slate-300"}`}
          style={{ width: syncing ? "55%" : response ? "100%" : "8%" }}
        />
      </div>

      <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <div>Yêu cầu: {requested}</div>
        <div>Đã tải: {fetched}</div>
        <div>Đã xử lý: {processed}</div>
        <div>Thời gian: {formatMs(metadata.elapsed_ms ?? elapsedMs)}</div>
      </div>
      {response?.calendars?.length ? (
        <div className="mt-2 text-xs text-slate-500">
          Lịch: {response.calendars.map((calendar) => calendar.summary).join(", ")}
        </div>
      ) : null}
      {response?.metadata?.finished_at ? <div className="mt-2 text-xs text-slate-500">Lần cuối: {response.metadata.finished_at}</div> : null}
      {error ? <div className="mt-3 rounded-md bg-red-50 p-2 text-xs text-red-700">{error}</div> : null}
      {response?.message ? <div className="mt-3 rounded-md bg-amber-50 p-2 text-xs text-amber-700">{response.message}</div> : null}
    </div>
  );
}

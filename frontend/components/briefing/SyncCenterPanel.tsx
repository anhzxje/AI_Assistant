"use client";

import type { SyncResponse } from "@/lib/api";
import { SyncProgressCard } from "./SyncProgressCard";

export function SyncCenterPanel({
  gmailSyncing,
  calendarSyncing,
  gmailResponse,
  calendarResponse,
  gmailError,
  calendarError,
  elapsedMs
}: {
  gmailSyncing: boolean;
  calendarSyncing: boolean;
  gmailResponse: SyncResponse | null;
  calendarResponse: SyncResponse | null;
  gmailError: string | null;
  calendarError: string | null;
  elapsedMs: number;
}) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-2">
        <SyncProgressCard title="Gmail sync" syncing={gmailSyncing} response={gmailResponse} error={gmailError} elapsedMs={elapsedMs} />
        <SyncProgressCard title="Calendar sync" syncing={calendarSyncing} response={calendarResponse} error={calendarError} elapsedMs={elapsedMs} />
      </div>
      <section className="rounded-lg border border-line bg-white p-5">
        <h2 className="text-sm font-semibold text-ink">Ghi chú</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Đồng bộ hiện chạy theo request đồng bộ thông thường. Nếu tác vụ lâu, thẻ tiến trình vẫn hiển thị số bản ghi đã xử lý sau khi hoàn tất và không giữ spinner vô hạn.
        </p>
      </section>
    </div>
  );
}

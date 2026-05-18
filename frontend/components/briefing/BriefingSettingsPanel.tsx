"use client";

import type { GoogleIntegrationStatus } from "@/lib/api";
import type { AuthSession } from "@/lib/api";

export function BriefingSettingsPanel({
  session,
  status
}: {
  session: AuthSession | null;
  status: GoogleIntegrationStatus | null;
}) {
  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-line bg-white p-5">
        <h2 className="text-lg font-semibold text-ink">Settings</h2>
        <p className="mt-1 text-sm text-slate-500">Trạng thái tài khoản và phạm vi dữ liệu dùng cho briefing.</p>
        <div className="mt-4 grid gap-3 text-sm text-slate-700">
          <StatusRow label="Đăng nhập" value={status?.google_login_email ?? session?.user.email ?? "Chưa rõ"} />
          <StatusRow label="Gmail" value={status?.gmail_connected ? `Đã kết nối${status.gmail_account_email ? ` · ${status.gmail_account_email}` : ""}` : "Chưa kết nối"} />
          <StatusRow label="Calendar" value={status?.calendar_connected ? `Đã kết nối${status.calendar_account_email ? ` · ${status.calendar_account_email}` : ""}` : "Chưa kết nối"} />
        </div>
      </section>
      <section className="rounded-lg border border-line bg-white p-5">
        <h3 className="text-sm font-semibold text-ink">Quyền riêng tư</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Gmail và Calendar chỉ dùng quyền đọc. Lumi không gửi email, không đánh dấu đã đọc, không xóa email và không tạo hoặc sửa sự kiện lịch.
        </p>
      </section>
    </div>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-panel px-3 py-2">
      <span className="font-medium text-slate-600">{label}</span>
      <span className="text-slate-800">{value}</span>
    </div>
  );
}

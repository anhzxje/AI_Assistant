"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CalendarDays, CheckCircle2, Chrome, Inbox, Loader2, PlugZap, Unplug, type LucideIcon } from "lucide-react";
import {
  GoogleIntegrationStatus,
  disconnectGoogleIntegration,
  fetchGoogleIntegrationStatus,
  getGoogleIntegrationStartUrl
} from "@/lib/api";
import { useAuthSession } from "@/lib/auth";

export default function SettingsPage() {
  const router = useRouter();
  const { session, ready } = useAuthSession();
  const [status, setStatus] = useState<GoogleIntegrationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setError(params.get("error"));
    setConnected(params.get("connected"));
  }, []);

  useEffect(() => {
    if (ready && !session) {
      router.replace("/login");
    }
  }, [ready, router, session]);

  useEffect(() => {
    if (!session) return;
    refreshStatus();
  }, [session]);

  async function refreshStatus() {
    setLoading(true);
    setError(null);
    try {
      setStatus(await fetchGoogleIntegrationStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được trạng thái tích hợp.");
    } finally {
      setLoading(false);
    }
  }

  async function connect(integration: "gmail" | "calendar") {
    setActionLoading(integration);
    setError(null);
    try {
      const url = await getGoogleIntegrationStartUrl(integration);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không mở được luồng kết nối Google.");
      setActionLoading(null);
    }
  }

  async function disconnect(integration: "gmail" | "calendar") {
    setActionLoading(integration);
    setError(null);
    try {
      await disconnectGoogleIntegration(integration);
      await refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không ngắt được kết nối Google.");
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-ink">Cài đặt và tích hợp</h1>
        <p className="mt-1 text-sm text-slate-500">
          Quản lý trạng thái đăng nhập và các ứng dụng kết nối cho {session?.user.email ?? "tài khoản hiện tại"}.
        </p>
      </div>

      {connected ? (
        <div className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
          <CheckCircle2 className="h-4 w-4" />
          Đã kết nối {connected === "gmail" ? "Gmail" : "Calendar"} ở chế độ đọc.
        </div>
      ) : null}
      {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

      <section className="rounded-lg border border-line bg-white">
        <div className="border-b border-line px-5 py-4">
          <h2 className="text-base font-semibold text-ink">Google</h2>
          <p className="mt-1 text-sm text-slate-500">
            Đăng nhập Google chỉ xác thực danh tính. Gmail và Calendar cần cấp quyền riêng, chỉ dùng chế độ đọc.
          </p>
        </div>
        <div className="grid gap-3 p-5 md:grid-cols-3">
          {loading || !ready ? (
            <div className="col-span-full flex items-center gap-2 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Đang tải trạng thái tích hợp...
            </div>
          ) : (
            <>
              <IntegrationCard
                icon={Chrome}
                title="Google Login"
                status={status?.google_login_configured ? "Đã cấu hình" : "Chưa cấu hình"}
                description={`Scope: ${(status?.required_scopes.login ?? ["openid", "email", "profile"]).join(", ")}${
                  status?.google_login_email ? `\nĐăng nhập: ${status.google_login_email}` : `\nĐăng nhập: ${session?.user.email ?? "chưa rõ"}`
                }`}
                active={Boolean(status?.google_login_configured)}
              />
              <IntegrationCard
                icon={Inbox}
                title="Gmail"
                status={status?.gmail_connected ? "Đã kết nối" : "Chưa kết nối"}
                description={`Scope: ${(status?.required_scopes.gmail_readonly ?? ["gmail.readonly"]).join(", ")}${
                  status?.gmail_account_email ? `\nTài khoản: ${status.gmail_account_email}` : ""
                }${status?.gmail_last_sync_at ? `\nSync gần nhất: ${status.gmail_last_sync_at}` : ""}${
                  status?.gmail_account_mismatch ? "\nCảnh báo: tài khoản Gmail khác với tài khoản đăng nhập." : ""
                }`}
                active={Boolean(status?.gmail_connected)}
                actionLabel={status?.gmail_connected ? "Ngắt kết nối Gmail" : "Kết nối Gmail"}
                actionIcon={status?.gmail_connected ? Unplug : PlugZap}
                actionLoading={actionLoading === "gmail"}
                disabled={!status?.google_login_configured}
                onAction={() => (status?.gmail_connected ? disconnect("gmail") : connect("gmail"))}
              />
              <IntegrationCard
                icon={CalendarDays}
                title="Calendar"
                status={status?.calendar_connected ? "Đã kết nối" : "Chưa kết nối"}
                description={`Scope: ${(status?.required_scopes.calendar_readonly ?? ["calendar.readonly"]).join(", ")}${
                  status?.calendar_account_email ? `\nTài khoản: ${status.calendar_account_email}` : ""
                }${status?.calendar_last_sync_at ? `\nSync gần nhất: ${status.calendar_last_sync_at}` : ""}${
                  status?.calendar_account_mismatch ? "\nCảnh báo: tài khoản Calendar khác với tài khoản đăng nhập." : ""
                }`}
                active={Boolean(status?.calendar_connected)}
                actionLabel={status?.calendar_connected ? "Ngắt kết nối Calendar" : "Kết nối Calendar"}
                actionIcon={status?.calendar_connected ? Unplug : PlugZap}
                actionLoading={actionLoading === "calendar"}
                disabled={!status?.google_login_configured}
                onAction={() => (status?.calendar_connected ? disconnect("calendar") : connect("calendar"))}
              />
            </>
          )}
        </div>
      </section>
    </div>
  );
}

function IntegrationCard({
  icon: Icon,
  title,
  status,
  description,
  active,
  actionLabel,
  actionIcon: ActionIcon,
  actionLoading,
  disabled,
  onAction
}: {
  icon: LucideIcon;
  title: string;
  status: string;
  description: string;
  active?: boolean;
  actionLabel?: string;
  actionIcon?: LucideIcon;
  actionLoading?: boolean;
  disabled?: boolean;
  onAction?: () => void;
}) {
  const ButtonIcon = ActionIcon ?? PlugZap;
  return (
    <div className="rounded-lg border border-line p-4">
      <div className="flex items-center gap-2">
        <div className={`flex h-9 w-9 items-center justify-center rounded-md ${active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
          <Icon className="h-4 w-4" />
        </div>
        <div>
          <div className="text-sm font-semibold text-ink">{title}</div>
          <div className="text-xs text-slate-500">{status}</div>
        </div>
      </div>
      <p className="mt-3 min-h-12 whitespace-pre-line text-sm leading-5 text-slate-600">{description}</p>
      {actionLabel ? (
        <button
          type="button"
          disabled={disabled || actionLoading}
          onClick={onAction}
          className="focus-ring mt-4 inline-flex h-9 w-full items-center justify-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {actionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ButtonIcon className="h-4 w-4" />}
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}

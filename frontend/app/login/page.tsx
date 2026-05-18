"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Chrome, KeyRound, Loader2, ShieldCheck } from "lucide-react";
import { APP_NAME, APP_TAGLINE, AppLogo } from "@/components/brand/AppLogo";
import { BACKEND_URL, GoogleLoginStatus, fetchGoogleLoginStatus, login } from "@/lib/api";
import { setStoredAuth } from "@/lib/auth";

const demoAccounts = [
  { label: "Người quản lý", email: "admin@omni.local", password: "admin123456", target: "/dashboard" },
  { label: "Người dùng", email: "user@omni.local", password: "user123456", target: "/" },
  { label: "Người dùng 2", email: "user2@omni.local", password: "user2123456", target: "/" }
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleStatus, setGoogleStatus] = useState<GoogleLoginStatus | null>(null);
  const [googleLoading, setGoogleLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const errorParam = params.get("error");
    if (errorParam) setError(errorParam);

    fetchGoogleLoginStatus()
      .then(setGoogleStatus)
      .catch(() =>
        setGoogleStatus({
          configured: false,
          scopes: ["openid", "email", "profile"],
          redirect_uri: "",
          message: "Google Login chưa được cấu hình trên máy này."
        })
      )
      .finally(() => setGoogleLoading(false));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const session = await login(email, password);
      setStoredAuth(session);
      router.push(session.user.role === "admin" ? "/dashboard" : "/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại.");
    } finally {
      setLoading(false);
    }
  }

  function startGoogleLogin() {
    if (!googleStatus?.configured) return;
    window.location.href = `${BACKEND_URL}/api/auth/google/start`;
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-96px)] max-w-6xl items-center justify-center px-2 py-8">
      <div className="grid w-full overflow-hidden rounded-lg border border-line bg-white shadow-sm lg:grid-cols-[0.95fr_1.05fr]">
        <section className="border-b border-line bg-slate-950 p-6 text-white lg:border-b-0 lg:border-r">
          <div className="flex h-full min-h-[420px] flex-col justify-between gap-8">
            <div>
              <div className="inline-flex rounded-lg bg-white p-2">
                <AppLogo compact />
              </div>
              <h1 className="mt-6 text-2xl font-semibold tracking-normal">{`Đăng nhập vào ${APP_NAME}`}</h1>
              <p className="mt-3 max-w-md text-sm leading-6 text-slate-300">{APP_TAGLINE}</p>
            </div>

            <div className="grid gap-3 text-sm">
              <div className="rounded-lg border border-white/10 bg-white/5 p-4">
                <div className="flex items-center gap-2 font-medium">
                  <ShieldCheck className="h-4 w-4 text-emerald-300" />
                  Phân quyền rõ ràng
                </div>
                <p className="mt-2 leading-6 text-slate-300">
                  Người dùng dùng chat, ghi nhớ và briefing. Người quản lý có thêm dashboard và công cụ quản trị dữ liệu.
                </p>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-xs leading-5 text-slate-300">
                Google Login chỉ dùng <span className="font-medium text-white">openid, email, profile</span>. Gmail và Calendar sẽ có luồng kết nối riêng.
              </div>
            </div>
          </div>
        </section>

        <main className="p-6 sm:p-8">
          <div className="mx-auto max-w-md">
            <div className="mb-6">
              <AppLogo />
              <p className="mt-4 text-sm leading-6 text-slate-600">
                Đăng nhập để đồng bộ lịch sử trò chuyện, bộ nhớ cá nhân và quyền truy cập theo vai trò.
              </p>
            </div>

            {error ? (
              <div className="mb-4 flex gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            ) : null}

            <button
              type="button"
              onClick={startGoogleLogin}
              disabled={googleLoading || !googleStatus?.configured}
              className="focus-ring inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {googleLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Chrome className="h-4 w-4" />}
              Tiếp tục với Google
            </button>
            {!googleLoading && !googleStatus?.configured ? (
              <p className="mt-2 text-xs leading-5 text-slate-500">Google Login chưa được cấu hình trên máy này.</p>
            ) : null}

            <div className="my-6 flex items-center gap-3 text-xs text-slate-400">
              <div className="h-px flex-1 bg-line" />
              <span>Tài khoản nội bộ</span>
              <div className="h-px flex-1 bg-line" />
            </div>

            <form onSubmit={submit} className="grid gap-4">
              <label className="grid gap-2 text-sm font-medium text-slate-700">
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="focus-ring h-10 rounded-md border border-line px-3 text-sm"
                  autoComplete="email"
                  placeholder="name@example.com"
                />
              </label>
              <label className="grid gap-2 text-sm font-medium text-slate-700">
                Mật khẩu
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="focus-ring h-10 rounded-md border border-line px-3 text-sm"
                  autoComplete="current-password"
                  placeholder="••••••••"
                />
              </label>

              <button
                type="submit"
                disabled={loading || !email.trim() || !password}
                className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-md border border-line bg-white px-4 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                Đăng nhập bằng tài khoản nội bộ
              </button>
            </form>

            <details className="mt-6 rounded-md border border-dashed border-line bg-slate-50 p-3 text-sm">
              <summary className="cursor-pointer font-medium text-slate-700">Dành cho demo/local development</summary>
              <div className="mt-3 grid gap-2">
                {demoAccounts.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => {
                      setEmail(account.email);
                      setPassword(account.password);
                    }}
                    className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-left hover:bg-slate-50"
                  >
                    <div className="font-medium text-ink">{account.label}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {account.email} / {account.password}
                    </div>
                  </button>
                ))}
              </div>
            </details>
          </div>
        </main>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { AppLogo } from "@/components/brand/AppLogo";
import { fetchMeWithToken } from "@/lib/api";
import { setStoredAuth } from "@/lib/auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [message, setMessage] = useState("Đang hoàn tất đăng nhập...");

  useEffect(() => {
    async function finish() {
      const params = new URLSearchParams(window.location.search);
      const token = params.get("token");
      if (!token) {
        router.replace("/login?error=Thiếu token đăng nhập.");
        return;
      }
      try {
        const me = await fetchMeWithToken(token);
        if (!me.authenticated || !me.user) {
          throw new Error("Không xác thực được phiên đăng nhập.");
        }
        setStoredAuth({ access_token: token, token_type: "bearer", user: me.user });
        router.replace(me.user.role === "admin" ? "/dashboard" : "/");
      } catch (err) {
        setMessage(err instanceof Error ? err.message : "Đăng nhập thất bại.");
        router.replace("/login?error=Không hoàn tất được đăng nhập Google.");
      }
    }
    finish();
  }, [router]);

  return (
    <div className="flex min-h-[520px] items-center justify-center">
      <div className="rounded-lg border border-line bg-white p-6 text-center shadow-sm">
        <div className="flex justify-center">
          <AppLogo compact />
        </div>
        <Loader2 className="mx-auto mt-6 h-5 w-5 animate-spin text-brand" />
        <p className="mt-3 text-sm text-slate-600">{message}</p>
      </div>
    </div>
  );
}

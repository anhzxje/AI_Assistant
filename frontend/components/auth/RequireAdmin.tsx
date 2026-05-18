"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { ShieldAlert } from "lucide-react";
import { useAuthSession } from "@/lib/auth";

export function RequireAdmin({ children }: { children: ReactNode }) {
  const { ready, isAdmin } = useAuthSession();

  if (!ready) {
    return <div className="rounded-lg border border-line bg-white p-5 text-sm text-slate-500">Dang kiem tra dang nhap...</div>;
  }

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-2xl rounded-lg border border-amber-200 bg-amber-50 p-6 text-amber-900">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <h1 className="text-base font-semibold">Can quyen Nguoi quan ly</h1>
            <p className="mt-2 text-sm">Ban can dang nhap voi vai tro Nguoi quan ly de truy cap trang nay.</p>
            <Link
              href="/login"
              className="mt-4 inline-flex rounded-md bg-amber-900 px-3 py-2 text-sm font-medium text-white hover:bg-amber-800"
            >
              Chuyen sang Nguoi quan ly
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

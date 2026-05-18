"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { BarChart3, Brain, CalendarDays, Database, LogIn, LogOut, MessageSquareText, Network, Settings } from "lucide-react";
import { AppLogo } from "@/components/brand/AppLogo";
import { logout as logoutApi } from "@/lib/api";
import { setStoredAuth, useAuthSession } from "@/lib/auth";

const userNavItems = [
  { href: "/", label: "Chat", icon: MessageSquareText },
  { href: "/briefing", label: "Briefing", icon: CalendarDays },
  { href: "/knowledge", label: "Sơ đồ tri thức", icon: Network },
  { href: "/memory", label: "Memory", icon: Brain },
  { href: "/settings", label: "Settings", icon: Settings }
];

const adminNavItems = [
  ...userNavItems,
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/admin", label: "Admin", icon: Database }
];

export function AppNav() {
  const router = useRouter();
  const { session } = useAuthSession();
  const navItems = session?.user.role === "admin" ? adminNavItems : userNavItems;

  async function signOut() {
    try {
      await logoutApi();
    } catch {
      // Local logout still succeeds if backend is unavailable.
    }
    setStoredAuth(null);
    router.push("/login");
  }

  return (
    <header className="border-b border-line bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
        <div className="min-w-0">
          <AppLogo compact />
          <div className="truncate text-xs text-slate-500">
            {session ? `${session.user.role_label} | ${session.user.email}` : "Bạn chưa đăng nhập"}
          </div>
        </div>
        <nav className="flex shrink-0 items-center gap-1 overflow-x-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="focus-ring inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
          {session ? (
            <button
              type="button"
              onClick={signOut}
              className="focus-ring inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Đăng xuất</span>
            </button>
          ) : (
            <Link
              href="/login"
              className="focus-ring inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              <LogIn className="h-4 w-4" />
              <span className="hidden sm:inline">Đăng nhập</span>
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}

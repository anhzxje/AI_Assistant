"use client";

import type { ReactNode } from "react";
import { RefreshCw } from "lucide-react";

type AdminTopbarProps = {
  title: string;
  subtitle?: string;
  loading?: boolean;
  onRefresh?: () => void;
  actions?: ReactNode;
};

export function AdminTopbar({ title, subtitle, loading, onRefresh, actions }: AdminTopbarProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line bg-white px-4 py-4">
      <div className="min-w-0">
        <h1 className="truncate text-xl font-semibold tracking-normal text-ink">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        {actions}
        {onRefresh ? (
          <button
            type="button"
            onClick={onRefresh}
            className="focus-ring inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            Refresh
          </button>
        ) : null}
      </div>
    </div>
  );
}

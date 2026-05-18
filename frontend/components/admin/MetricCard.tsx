"use client";

import type { LucideIcon } from "lucide-react";

type MetricCardProps = {
  label: string;
  value: string | number;
  helper?: string;
  trend?: string;
  icon?: LucideIcon;
  tone?: "neutral" | "good" | "warning" | "danger" | "info";
  active?: boolean;
  onClick?: () => void;
};

const toneClass = {
  neutral: "border-line bg-white",
  good: "border-emerald-200 bg-emerald-50",
  warning: "border-amber-200 bg-amber-50",
  danger: "border-red-200 bg-red-50",
  info: "border-cyan-200 bg-cyan-50"
};

export function MetricCard({ label, value, helper, trend, icon: Icon, tone = "neutral", active, onClick }: MetricCardProps) {
  const content = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-xs font-medium uppercase tracking-normal text-slate-500">{label}</div>
          <div className="mt-2 text-2xl font-semibold tracking-normal text-ink">{value}</div>
        </div>
        {Icon ? (
          <span className="rounded-md border border-white/60 bg-white/70 p-2 text-slate-600">
            <Icon className="h-4 w-4" />
          </span>
        ) : null}
      </div>
      {helper || trend ? (
        <div className="mt-3 flex items-center justify-between gap-3 text-xs text-slate-500">
          <span className="min-w-0 truncate">{helper}</span>
          {trend ? <span className="shrink-0 font-medium text-slate-700">{trend}</span> : null}
        </div>
      ) : null}
    </>
  );

  const className = `rounded-lg border p-4 text-left shadow-sm transition ${toneClass[tone]} ${
    active ? "ring-2 ring-brand ring-offset-2" : ""
  } ${onClick ? "focus-ring cursor-pointer hover:border-brand" : ""}`;

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className}>
        {content}
      </button>
    );
  }

  return <div className={className}>{content}</div>;
}

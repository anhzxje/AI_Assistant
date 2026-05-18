"use client";

import { Loader2 } from "lucide-react";

export function ReportDraftPanel({
  period,
  style,
  loading,
  onPeriodChange,
  onStyleChange,
  onGenerate
}: {
  period: "today" | "7d" | "30d";
  style: "student" | "admin" | "research";
  loading: boolean;
  onPeriodChange: (value: "today" | "7d" | "30d") => void;
  onStyleChange: (value: "student" | "admin" | "research") => void;
  onGenerate: () => void;
}) {
  return (
    <section className="rounded-lg border border-line bg-white p-4">
      <h2 className="text-base font-semibold text-ink">Báo cáo</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="text-sm font-medium text-slate-700">
          Kỳ báo cáo
          <select value={period} onChange={(event) => onPeriodChange(event.target.value as any)} className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm">
            <option value="today">Hôm nay</option>
            <option value="7d">7 ngày</option>
            <option value="30d">30 ngày</option>
          </select>
        </label>
        <label className="text-sm font-medium text-slate-700">
          Phong cách
          <select value={style} onChange={(event) => onStyleChange(event.target.value as any)} className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm">
            <option value="student">Student</option>
            <option value="admin">Admin</option>
            <option value="research">Research</option>
          </select>
        </label>
      </div>
      <button type="button" onClick={onGenerate} disabled={loading} className="focus-ring mt-4 inline-flex h-10 items-center gap-2 rounded-md bg-brand px-4 text-sm font-medium text-white hover:bg-cyan-800 disabled:bg-slate-300">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Tạo báo cáo
      </button>
    </section>
  );
}


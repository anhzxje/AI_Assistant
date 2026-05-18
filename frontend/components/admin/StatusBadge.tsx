"use client";

type StatusBadgeProps = {
  value: string | number | null | undefined;
  tone?: Tone;
};

type Tone = "neutral" | "good" | "warning" | "danger" | "info";

const toneClass = {
  neutral: "border-slate-200 bg-slate-50 text-slate-700",
  good: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-red-200 bg-red-50 text-red-700",
  info: "border-cyan-200 bg-cyan-50 text-cyan-700"
};

export function StatusBadge({ value, tone }: StatusBadgeProps) {
  const label = String(value ?? "unknown");
  const resolvedTone = tone ?? inferTone(label);
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${toneClass[resolvedTone]}`}>
      {label.replaceAll("_", " ")}
    </span>
  );
}

function inferTone(value: string): Tone {
  const normalized = value.toLowerCase();
  if (["success", "healthy", "available", "ok", "reviewed", "promoted_to_eval"].includes(normalized)) return "good";
  if (["pending", "running", "review", "queued_for_reindex", "queued_for_recrawl", "medium"].includes(normalized)) return "warning";
  if (["failed", "unavailable", "high", "missing_features", "down"].includes(normalized)) return "danger";
  if (["info", "embedded", "low", "up"].includes(normalized)) return "info";
  return "neutral";
}

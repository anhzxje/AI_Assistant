import { AlertTriangle, CheckCircle2, Gauge } from "lucide-react";
import type { QualityMetadata } from "@/lib/types";

function normalizeScore(quality?: QualityMetadata): number | null {
  if (!quality || typeof quality.quality_score !== "number") return null;
  return Math.max(0, Math.min(1, quality.quality_score));
}

export function QualityBadge({ quality }: { quality?: QualityMetadata }) {
  const score = normalizeScore(quality);
  const review = Boolean(quality?.requires_admin_review);
  const issues = quality?.issues?.length ?? 0;

  if (score === null) {
    return (
      <span className="inline-flex h-6 items-center gap-1 rounded-full border border-slate-200 bg-white px-2 text-xs font-medium text-slate-600">
        <Gauge className="h-3.5 w-3.5" />
        Quality n/a
      </span>
    );
  }

  const pct = Math.round(score * 100);
  const className =
    score >= 0.78 && !review
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : score >= 0.55
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-red-200 bg-red-50 text-red-700";
  const Icon = review || issues > 0 ? AlertTriangle : CheckCircle2;

  return (
    <span className={`inline-flex h-6 items-center gap-1 rounded-full border px-2 text-xs font-medium ${className}`} title={issues ? `${issues} quality issue(s)` : "No quality issue reported"}>
      <Icon className="h-3.5 w-3.5" />
      {pct}%
    </span>
  );
}

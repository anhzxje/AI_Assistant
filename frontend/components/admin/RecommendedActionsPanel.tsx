"use client";

import { AlertTriangle, CheckCircle2, PlayCircle } from "lucide-react";
import type { MissingKnowledgeIndicator } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

type RecommendedActionsPanelProps = {
  feedbackActions?: string[];
  missingIndicators?: MissingKnowledgeIndicator[];
  onRunAllJobs?: () => void;
};

export function RecommendedActionsPanel({
  feedbackActions = [],
  missingIndicators = [],
  onRunAllJobs
}: RecommendedActionsPanelProps) {
  const actions = buildActions(feedbackActions, missingIndicators);
  return (
    <section className="rounded-lg border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink">Recommended Actions</h2>
          <p className="mt-1 text-sm text-slate-500">Operational next steps derived from feedback, QA, and data signals.</p>
        </div>
        {onRunAllJobs ? (
          <button
            type="button"
            onClick={onRunAllJobs}
            className="focus-ring inline-flex items-center gap-2 rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-cyan-800"
          >
            <PlayCircle className="h-4 w-4" />
            Run jobs
          </button>
        ) : null}
      </div>
      <div className="mt-4 grid gap-3">
        {actions.map((action) => {
          const Icon = action.severity === "low" ? CheckCircle2 : AlertTriangle;
          return (
            <div key={`${action.label}-${action.action}`} className="rounded-md border border-line bg-panel p-3">
              <div className="flex items-start gap-3">
                <Icon className={action.severity === "high" ? "mt-0.5 h-4 w-4 text-red-600" : "mt-0.5 h-4 w-4 text-amber-600"} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-ink">{action.label}</span>
                    <StatusBadge value={action.severity} />
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{action.action}</p>
                </div>
                <span className="rounded-md bg-white px-2 py-1 text-xs font-semibold text-slate-700">{action.count}</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function buildActions(feedbackActions: string[], indicators: MissingKnowledgeIndicator[]) {
  const indicatorActions = indicators.map((item) => ({
    label: item.label,
    action: item.action,
    count: item.count,
    severity: item.severity
  }));
  const feedback = feedbackActions.map((action, index) => ({
    label: "Feedback cluster",
    action,
    count: index + 1,
    severity: action.toLowerCase().includes("no urgent") ? "low" : "medium"
  }));
  const combined = [...indicatorActions, ...feedback];
  if (combined.length) return combined;
  return [
    {
      label: "No urgent action",
      action: "Keep monitoring feedback, QA reports, and source freshness.",
      count: 0,
      severity: "low"
    }
  ];
}

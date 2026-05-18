"use client";

import { CheckCircle2, XCircle } from "lucide-react";
import type { AdminSystemSummary } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

type QAEvaluationPanelProps = {
  summary: AdminSystemSummary | null;
};

export function QAEvaluationPanel({ summary }: QAEvaluationPanelProps) {
  const retrieval = summary?.qa.retrieval_eval ?? {};
  const rag = summary?.qa.rag_eval ?? {};
  const feedback = summary?.qa.feedback_eval ?? {};
  const failedRetrieval = (retrieval.results ?? []).filter((item: any) => item.type_hit === false).slice(0, 6);
  const failedFeedback = (feedback.results ?? []).filter((item: any) => item.passed === false).slice(0, 6);

  return (
    <section className="rounded-lg border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink">QA & Evaluation</h2>
          <p className="mt-1 text-sm text-slate-500">Retrieval relevance, grounded answers, and feedback regression checks.</p>
        </div>
        <StatusBadge value={`${summary?.qa.feedback_eval?.passed_cases ?? 0} feedback passes`} tone="info" />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <ScoreCard label="Retrieval hit rate" value={retrieval.document_type_hit_rate} helper={`${retrieval.total_cases ?? 0} cases`} />
        <ScoreCard label="Keyword hit rate" value={retrieval.average_keyword_hit_rate} helper="Average expected keyword overlap" />
        <ScoreCard label="Groundedness" value={rag.average_groundedness_score} helper={`${rag.total_cases ?? 0} RAG cases`} />
        <ScoreCard label="Feedback eval pass" value={feedback.pass_rate} helper={`${feedback.passed_cases ?? 0}/${feedback.total_cases ?? 0} cases`} />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <FailedCaseTable title="Retrieval misses" rows={failedRetrieval} mode="retrieval" />
        <FailedCaseTable title="Feedback eval failures" rows={failedFeedback} mode="feedback" />
      </div>
    </section>
  );
}

function ScoreCard({ label, value, helper }: { label: string; value: number | undefined; helper: string }) {
  const percent = typeof value === "number" ? Math.round(value * 100) : 0;
  const tone = percent >= 80 ? "text-emerald-700" : percent >= 50 ? "text-amber-700" : "text-red-700";
  return (
    <div className="rounded-md border border-line bg-panel p-3">
      <div className="text-xs font-medium uppercase tracking-normal text-slate-500">{label}</div>
      <div className={`mt-2 text-2xl font-semibold ${tone}`}>{typeof value === "number" ? `${percent}%` : "-"}</div>
      <div className="mt-2 h-2 rounded-full bg-white">
        <div className="h-2 rounded-full bg-brand" style={{ width: `${Math.max(0, Math.min(100, percent))}%` }} />
      </div>
      <div className="mt-2 text-xs text-slate-500">{helper}</div>
    </div>
  );
}

function FailedCaseTable({ title, rows, mode }: { title: string; rows: any[]; mode: "retrieval" | "feedback" }) {
  return (
    <div className="rounded-md border border-line">
      <div className="border-b border-line bg-slate-50 px-3 py-2 text-sm font-medium text-ink">{title}</div>
      <div className="max-h-80 overflow-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="border-b border-line text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">Case</th>
              <th className="px-3 py-2">Expected</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((row, index) => (
              <tr key={`${title}-${index}`}>
                <td className="max-w-[300px] px-3 py-2 text-slate-700">
                  <div className="line-clamp-2">{row.query || "(no query)"}</div>
                </td>
                <td className="px-3 py-2 text-slate-600">
                  {mode === "retrieval" ? row.expected_document_type || "unknown" : row.expected_behavior || row.reason || "quality"}
                </td>
                <td className="px-3 py-2">
                  {mode === "retrieval" ? (
                    row.type_hit ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <XCircle className="h-4 w-4 text-red-600" />
                  ) : row.passed ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" />
                  )}
                </td>
              </tr>
            ))}
            {!rows.length ? (
              <tr>
                <td className="px-3 py-4 text-slate-500" colSpan={3}>
                  No failed cases in the current report.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

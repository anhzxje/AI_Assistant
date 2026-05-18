"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, BarChart3, Database, Inbox, ListChecks, RefreshCw, ServerCog, ShieldCheck } from "lucide-react";
import {
  AdminDocument,
  AdminDocumentDetail,
  AdminSystemSummary,
  DataLayerSummary,
  FeedbackRecord,
  JobRecord,
  fetchDocuments,
  fetchDocumentDetail,
  fetchDataLayerSummary,
  fetchFeedback,
  fetchJobs,
  fetchSystemSummary,
  promoteFeedbackToEval,
  queueFeedbackRecrawl,
  queueFeedbackReindex,
  runAllJobs,
  updateFeedback
} from "@/lib/api";
import { RequireAdmin } from "@/components/auth/RequireAdmin";
import { DataQualityPanel } from "@/components/admin/DataQualityPanel";
import { DataLayerPanel } from "@/components/admin/DataLayerPanel";
import { DocumentTable } from "@/components/admin/DocumentTable";
import { DocumentDetailDrawer } from "@/components/admin/DocumentDetailDrawer";
import { FeedbackInbox } from "@/components/admin/FeedbackInbox";
import { FilterBar } from "@/components/admin/FilterBar";
import { MetricCard } from "@/components/admin/MetricCard";
import { QAEvaluationPanel } from "@/components/admin/QAEvaluationPanel";
import { RecommendedActionsPanel } from "@/components/admin/RecommendedActionsPanel";
import { SourceHealthTable } from "@/components/admin/SourceHealthTable";
import { StatusBadge } from "@/components/admin/StatusBadge";

type FeedbackFilters = {
  status: string;
  reason: string;
  severity: string;
  intent: string;
};

export default function DashboardPage() {
  return (
    <RequireAdmin>
      <DashboardContent />
    </RequireAdmin>
  );
}

function DashboardContent() {
  const [summary, setSummary] = useState<AdminSystemSummary | null>(null);
  const [dataLayer, setDataLayer] = useState<DataLayerSummary | null>(null);
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [documentTotal, setDocumentTotal] = useState(0);
  const [feedback, setFeedback] = useState<FeedbackRecord[]>([]);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [selectedDetail, setSelectedDetail] = useState<AdminDocumentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [documentType, setDocumentType] = useState("all");
  const [domain, setDomain] = useState("all");
  const [feedbackFilters, setFeedbackFilters] = useState<FeedbackFilters>({
    status: "all",
    reason: "all",
    severity: "all",
    intent: "all"
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const system = await fetchSystemSummary();
      setSummary(system);
      setDataLayer(await fetchDataLayerSummary());
      await Promise.all([loadDocuments(documentType, domain), loadFeedback(feedbackFilters), loadJobs()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dashboard load failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadDocuments(nextType = documentType, nextDomain = domain) {
    const data = await fetchDocuments({
      documentType: nextType === "all" ? undefined : nextType,
      domain: nextDomain === "all" ? undefined : nextDomain,
      limit: 12
    });
    setDocuments(data.documents);
    setDocumentTotal(data.total);
  }

  async function loadFeedback(nextFilters = feedbackFilters) {
    const data = await fetchFeedback({ ...nextFilters, limit: 8 });
    setFeedback(data.feedback);
  }

  async function loadJobs() {
    const data = await fetchJobs({ limit: 8 });
    setJobs(data.jobs);
  }

  async function runFeedbackAction(feedbackId: string, action: "reviewed" | "eval" | "reindex" | "recrawl") {
    setMessage(null);
    try {
      if (action === "reviewed") await updateFeedback(feedbackId, { status: "reviewed", admin_note: "Reviewed from dashboard." });
      if (action === "eval") await promoteFeedbackToEval(feedbackId);
      if (action === "reindex") await queueFeedbackReindex(feedbackId);
      if (action === "recrawl") await queueFeedbackRecrawl(feedbackId);
      setMessage("Feedback action saved.");
      await Promise.all([fetchSystemSummary().then(setSummary), loadFeedback(), loadJobs()]);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Feedback action failed");
    }
  }

  async function runMaintenanceJobs() {
    setMessage(null);
    try {
      const result = await runAllJobs(false, 20);
      setMessage(result.message);
      await Promise.all([fetchSystemSummary().then(setSummary), loadJobs()]);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Job run failed");
    }
  }

  async function openDocument(document: AdminDocument) {
    setDetailLoading(true);
    setSelectedDetail(null);
    try {
      setSelectedDetail(await fetchDocumentDetail(document.document_id));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Document detail failed");
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadDocuments(documentType, domain).catch((err) => setError(err instanceof Error ? err.message : "Document filter failed"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentType, domain]);

  useEffect(() => {
    loadFeedback(feedbackFilters).catch((err) => setMessage(err instanceof Error ? err.message : "Feedback filter failed"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feedbackFilters]);

  const documentTypes = useMemo(() => Object.keys(summary?.data.chunks_by_document_type ?? {}), [summary]);
  const domains = useMemo(() => (summary?.data.top_domains ?? []).map((item) => item.domain), [summary]);
  const retrieval = summary?.qa.retrieval_eval ?? {};
  const rag = summary?.qa.rag_eval ?? {};
  const pendingJobs = summary?.jobs.pending ?? 0;
  const downvotes = summary?.feedback.by_rating?.down ?? 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-normal text-ink">BI Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Decision view for quality, coverage, feedback, and local maintenance.</p>
        </div>
        <button
          type="button"
          onClick={load}
          className="focus-ring inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          Refresh
        </button>
      </div>

      {error ? (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      ) : null}
      {message ? <div className="rounded-lg border border-line bg-white p-3 text-sm text-slate-600">{message}</div> : null}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Documents" value={summary?.data.total_documents ?? "-"} helper="Processed source records" icon={Database} />
        <MetricCard label="Chunks" value={summary?.data.total_chunks ?? "-"} helper={`${summary?.health.qdrant_points ?? 0} Qdrant points`} icon={BarChart3} />
        <MetricCard label="Retrieval hit rate" value={formatPercent(retrieval.document_type_hit_rate)} helper={`${retrieval.total_cases ?? 0} eval cases`} icon={ListChecks} />
        <MetricCard label="Groundedness" value={formatPercent(rag.average_groundedness_score)} helper={`${rag.total_cases ?? 0} RAG cases`} icon={ShieldCheck} />
        <MetricCard label="Feedback downvotes" value={downvotes} helper={`${summary?.feedback.total ?? 0} total records`} icon={Inbox} tone={downvotes ? "warning" : "good"} />
        <MetricCard label="Pending jobs" value={pendingJobs} helper="Queued local actions" icon={ServerCog} tone={pendingJobs ? "warning" : "good"} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <DistributionPanel
          title="Chunks by Document Type"
          data={summary?.data.chunks_by_document_type ?? {}}
          activeKey={documentType}
          onSelect={(key) => setDocumentType(key)}
        />
        <div className="grid gap-5">
          <DistributionPanel title="Feedback Reasons" data={summary?.feedback.by_reason ?? {}} activeKey={feedbackFilters.reason} onSelect={(reason) => setFeedbackFilters({ ...feedbackFilters, reason })} />
          <DistributionPanel title="Job Status" data={summary?.jobs ?? {}} activeKey="all" />
        </div>
      </div>

      <RecommendedActionsPanel
        feedbackActions={summary?.feedback.recommended_actions}
        missingIndicators={summary?.data.missing_knowledge_indicators}
        onRunAllJobs={runMaintenanceJobs}
      />

      <DataLayerPanel summary={dataLayer} />
      <DataQualityPanel summary={summary} />
      <QAEvaluationPanel summary={summary} />

      <SourceHealthTable
        sources={summary?.data.source_health ?? []}
        activeDomain={domain}
        onDomainSelect={(nextDomain) => setDomain(domain === nextDomain ? "all" : nextDomain)}
      />

      <FilterBar
        filters={[
          {
            id: "documentType",
            label: "Document type",
            value: documentType,
            onChange: setDocumentType,
            options: [{ label: "All document types", value: "all" }, ...documentTypes.map((type) => ({ label: type, value: type }))]
          },
          {
            id: "domain",
            label: "Domain",
            value: domain,
            onChange: setDomain,
            options: [{ label: "All domains", value: "all" }, ...domains.map((item) => ({ label: item, value: item }))]
          }
        ]}
        onReset={() => {
          setDocumentType("all");
          setDomain("all");
        }}
      />

      <DocumentTable documents={documents} total={documentTotal} activeDocumentId={selectedDetail?.document.document_id} onOpenDetail={openDocument} />

      <FeedbackInbox
        feedback={feedback}
        summary={summary?.feedback ?? null}
        filters={feedbackFilters}
        onFiltersChange={setFeedbackFilters}
        onRefresh={() => loadFeedback(feedbackFilters)}
        onAction={runFeedbackAction}
        message={message}
        compact
      />

      <DocumentDetailDrawer detail={selectedDetail} loading={detailLoading} onClose={() => setSelectedDetail(null)} />
    </div>
  );
}

function DistributionPanel({
  title,
  data,
  activeKey,
  onSelect
}: {
  title: string;
  data: Record<string, number>;
  activeKey: string;
  onSelect?: (key: string) => void;
}) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((sum, [, value]) => sum + value, 0);
  return (
    <section className="rounded-lg border border-line bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-ink">{title}</h2>
        <StatusBadge value={`${total} total`} tone="info" />
      </div>
      <div className="mt-4 space-y-3">
        {entries.map(([key, value]) => {
          const pct = total ? Math.round((value / total) * 100) : 0;
          const active = activeKey === key;
          const row = (
            <>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className={active ? "font-semibold text-brand" : "font-medium text-slate-700"}>{key.replaceAll("_", " ")}</span>
                <span className="tabular-nums text-slate-500">{value}</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-100">
                <div className={active ? "h-2 rounded-full bg-brand" : "h-2 rounded-full bg-accent"} style={{ width: `${pct}%` }} />
              </div>
            </>
          );
          if (onSelect) {
            return (
              <button
                key={key}
                type="button"
                onClick={() => onSelect(active ? "all" : key)}
                className={`focus-ring w-full rounded-md border p-3 text-left hover:border-brand ${
                  active ? "border-brand bg-cyan-50" : "border-line bg-panel"
                }`}
              >
                {row}
              </button>
            );
          }
          return (
            <div key={key} className="rounded-md border border-line bg-panel p-3">
              {row}
            </div>
          );
        })}
        {!entries.length ? <div className="rounded-md border border-line bg-panel p-4 text-sm text-slate-500">No data available.</div> : null}
      </div>
    </section>
  );
}

function formatPercent(value: number | undefined) {
  if (typeof value !== "number") return "-";
  return `${Math.round(value * 100)}%`;
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, BarChart3, Database, Inbox, ListChecks, ServerCog, ShieldCheck } from "lucide-react";
import {
  AdminDocument,
  AdminDocumentDetail,
  AdminSystemSummary,
  DataLayerSummary,
  FeedbackRecord,
  JobRecord,
  fetchDocumentDetail,
  fetchDocuments,
  fetchDataLayerSummary,
  fetchFeedback,
  fetchJobs,
  fetchSystemSummary,
  promoteFeedbackToEval,
  queueFeedbackRecrawl,
  queueFeedbackReindex,
  retryJob,
  runAllJobs,
  runNextJob,
  updateFeedback
} from "@/lib/api";
import { RequireAdmin } from "@/components/auth/RequireAdmin";
import { AdminSection } from "@/components/admin/AdminSidebar";
import { AdminShell } from "@/components/admin/AdminShell";
import { DataQualityPanel } from "@/components/admin/DataQualityPanel";
import { DataLayerPanel } from "@/components/admin/DataLayerPanel";
import { DocumentDetailDrawer } from "@/components/admin/DocumentDetailDrawer";
import { DocumentTable } from "@/components/admin/DocumentTable";
import { FeedbackInbox } from "@/components/admin/FeedbackInbox";
import { FilterBar } from "@/components/admin/FilterBar";
import { JobsPanel } from "@/components/admin/JobsPanel";
import { MetricCard } from "@/components/admin/MetricCard";
import { QAEvaluationPanel } from "@/components/admin/QAEvaluationPanel";
import { RecommendedActionsPanel } from "@/components/admin/RecommendedActionsPanel";
import { SourceHealthTable } from "@/components/admin/SourceHealthTable";

type FeedbackFilters = {
  status: string;
  reason: string;
  severity: string;
  intent: string;
};

export default function AdminPage() {
  return (
    <RequireAdmin>
      <AdminContent />
    </RequireAdmin>
  );
}

function AdminContent() {
  const [activeSection, setActiveSection] = useState<AdminSection>("overview");
  const [summary, setSummary] = useState<AdminSystemSummary | null>(null);
  const [dataLayer, setDataLayer] = useState<DataLayerSummary | null>(null);
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [documentTotal, setDocumentTotal] = useState(0);
  const [selectedDetail, setSelectedDetail] = useState<AdminDocumentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackRecord[]>([]);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [query, setQuery] = useState("");
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
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [jobsMessage, setJobsMessage] = useState<string | null>(null);

  async function loadAll() {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadSummary(), loadDocuments(), loadFeedback(), loadJobs()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Admin load failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadSummary() {
    setSummary(await fetchSystemSummary());
    setDataLayer(await fetchDataLayerSummary());
  }

  async function loadDocuments(nextQuery = query, nextType = documentType, nextDomain = domain) {
    const data = await fetchDocuments({
      q: nextQuery.trim() || undefined,
      documentType: nextType === "all" ? undefined : nextType,
      domain: nextDomain === "all" ? undefined : nextDomain,
      limit: 200
    });
    setDocuments(data.documents);
    setDocumentTotal(data.total);
  }

  async function loadFeedback(nextFilters = feedbackFilters) {
    const data = await fetchFeedback({ ...nextFilters, limit: 80 });
    setFeedback(data.feedback);
  }

  async function loadJobs() {
    const data = await fetchJobs({ limit: 80 });
    setJobs(data.jobs);
  }

  async function openDocument(document: AdminDocument) {
    setDetailLoading(true);
    setSelectedDetail(null);
    try {
      setSelectedDetail(await fetchDocumentDetail(document.document_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Document detail failed");
    } finally {
      setDetailLoading(false);
    }
  }

  async function runFeedbackAction(feedbackId: string, action: "reviewed" | "eval" | "reindex" | "recrawl") {
    setFeedbackMessage(null);
    try {
      if (action === "reviewed") await updateFeedback(feedbackId, { status: "reviewed", admin_note: "Reviewed from admin workspace." });
      if (action === "eval") await promoteFeedbackToEval(feedbackId);
      if (action === "reindex") await queueFeedbackReindex(feedbackId);
      if (action === "recrawl") await queueFeedbackRecrawl(feedbackId);
      setFeedbackMessage("Feedback action saved.");
      await Promise.all([loadSummary(), loadFeedback(), loadJobs()]);
    } catch (err) {
      setFeedbackMessage(err instanceof Error ? err.message : "Feedback action failed");
    }
  }

  async function runJobs(action: "next" | "all") {
    setJobsMessage(null);
    try {
      const result = action === "next" ? await runNextJob(false) : await runAllJobs(false, 20);
      setJobsMessage(result.message);
      await Promise.all([loadSummary(), loadJobs(), loadFeedback()]);
    } catch (err) {
      setJobsMessage(err instanceof Error ? err.message : "Job run failed");
    }
  }

  async function retry(jobId: string) {
    setJobsMessage(null);
    try {
      await retryJob(jobId);
      setJobsMessage("Job moved back to pending.");
      await Promise.all([loadSummary(), loadJobs()]);
    } catch (err) {
      setJobsMessage(err instanceof Error ? err.message : "Retry failed");
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadDocuments(query, documentType, domain).catch((err) => setError(err instanceof Error ? err.message : "Document filter failed"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentType, domain]);

  useEffect(() => {
    loadFeedback(feedbackFilters).catch((err) => setFeedbackMessage(err instanceof Error ? err.message : "Feedback filter failed"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feedbackFilters]);

  const documentTypes = useMemo(() => Object.keys(summary?.data.chunks_by_document_type ?? {}), [summary]);
  const domains = useMemo(() => (summary?.data.top_domains ?? []).map((item) => item.domain), [summary]);
  const retrieval = summary?.qa.retrieval_eval ?? {};
  const rag = summary?.qa.rag_eval ?? {};
  const sectionTitle = titleForSection(activeSection);

  return (
    <AdminShell
      title={sectionTitle.title}
      subtitle={sectionTitle.subtitle}
      activeSection={activeSection}
      onSectionChange={setActiveSection}
      loading={loading}
      onRefresh={loadAll}
    >
      {error ? (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      ) : null}

      {activeSection === "overview" ? (
        <div className="space-y-5">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <MetricCard label="Documents" value={summary?.data.total_documents ?? "-"} helper="Processed records" icon={Database} />
            <MetricCard label="Chunks" value={summary?.data.total_chunks ?? "-"} helper={`${summary?.health.qdrant_points ?? 0} Qdrant points`} icon={BarChart3} />
            <MetricCard label="Retrieval" value={formatPercent(retrieval.document_type_hit_rate)} helper="Type hit rate" icon={ListChecks} />
            <MetricCard label="Groundedness" value={formatPercent(rag.average_groundedness_score)} helper="RAG groundedness" icon={ShieldCheck} />
            <MetricCard label="Feedback" value={summary?.feedback.total ?? 0} helper={`${summary?.feedback.by_status.new ?? 0} new`} icon={Inbox} />
            <MetricCard label="Pending jobs" value={summary?.jobs.pending ?? 0} helper={`${summary?.jobs.failed ?? 0} failed`} icon={ServerCog} />
          </div>
          <RecommendedActionsPanel
            feedbackActions={summary?.feedback.recommended_actions}
            missingIndicators={summary?.data.missing_knowledge_indicators}
            onRunAllJobs={() => runJobs("all")}
          />
          <DataLayerPanel summary={dataLayer} />
          <DataQualityPanel summary={summary} />
        </div>
      ) : null}

      {activeSection === "sources" ? (
        <div className="space-y-5">
          <SourceHealthTable
            sources={summary?.data.source_health ?? []}
            activeDomain={domain}
            onDomainSelect={(nextDomain) => setDomain(domain === nextDomain ? "all" : nextDomain)}
          />
          <DocumentFilters
            query={query}
            setQuery={setQuery}
            documentType={documentType}
            setDocumentType={setDocumentType}
            domain={domain}
            setDomain={setDomain}
            documentTypes={documentTypes}
            domains={domains}
            onApply={() => loadDocuments(query, documentType, domain)}
          />
          <DocumentTable documents={documents} total={documentTotal} activeDocumentId={selectedDetail?.document.document_id} onOpenDetail={openDocument} />
        </div>
      ) : null}

      {activeSection === "qa" ? <QAEvaluationPanel summary={summary} /> : null}

      {activeSection === "feedback" ? (
        <FeedbackInbox
          feedback={feedback}
          summary={summary?.feedback ?? null}
          filters={feedbackFilters}
          onFiltersChange={setFeedbackFilters}
          onRefresh={() => loadFeedback(feedbackFilters)}
          onAction={runFeedbackAction}
          message={feedbackMessage}
        />
      ) : null}

      {activeSection === "jobs" ? (
        <JobsPanel
          jobs={jobs}
          message={jobsMessage}
          onRefresh={loadJobs}
          onRunNext={() => runJobs("next")}
          onRunAll={() => runJobs("all")}
          onRetry={retry}
        />
      ) : null}

      {activeSection === "knowledge" ? (
        <div className="space-y-5">
          <DocumentFilters
            query={query}
            setQuery={setQuery}
            documentType={documentType}
            setDocumentType={setDocumentType}
            domain={domain}
            setDomain={setDomain}
            documentTypes={documentTypes}
            domains={domains}
            onApply={() => loadDocuments(query, documentType, domain)}
          />
          <DocumentTable documents={documents} total={documentTotal} activeDocumentId={selectedDetail?.document.document_id} onOpenDetail={openDocument} />
        </div>
      ) : null}

      <DocumentDetailDrawer detail={selectedDetail} loading={detailLoading} onClose={() => setSelectedDetail(null)} />
    </AdminShell>
  );
}

function DocumentFilters({
  query,
  setQuery,
  documentType,
  setDocumentType,
  domain,
  setDomain,
  documentTypes,
  domains,
  onApply
}: {
  query: string;
  setQuery: (value: string) => void;
  documentType: string;
  setDocumentType: (value: string) => void;
  domain: string;
  setDomain: (value: string) => void;
  documentTypes: string[];
  domains: string[];
  onApply: () => void;
}) {
  return (
    <FilterBar
      searchValue={query}
      searchPlaceholder="Search title, URL, or text..."
      onSearchChange={setQuery}
      onSearchSubmit={onApply}
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
        setQuery("");
        setDocumentType("all");
        setDomain("all");
      }}
    />
  );
}

function titleForSection(section: AdminSection) {
  const titles: Record<AdminSection, { title: string; subtitle: string }> = {
    overview: {
      title: "Admin Overview",
      subtitle: "System health, knowledge coverage, quality indicators, and recommended actions."
    },
    sources: {
      title: "Data Sources",
      subtitle: "Domain freshness, source authority, duplicate signals, and source-filtered documents."
    },
    qa: {
      title: "QA & Evaluation",
      subtitle: "Retrieval, groundedness, data quality, and feedback eval reports."
    },
    feedback: {
      title: "Feedback Inbox",
      subtitle: "Review user feedback and queue eval, reindex, or recrawl actions."
    },
    jobs: {
      title: "Jobs",
      subtitle: "Run and retry local maintenance jobs created by admin actions."
    },
    knowledge: {
      title: "Knowledge Admin",
      subtitle: "Search documents, inspect source metadata, and preview chunks."
    }
  };
  return titles[section];
}

function formatPercent(value: number | undefined) {
  if (typeof value !== "number") return "-";
  return `${Math.round(value * 100)}%`;
}

"use client";

import { AlertCircle, Info, Loader2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import type { KnowledgeGraph, KnowledgeNode } from "@/lib/api";
import { fetchKnowledgeGraph } from "@/lib/api";
import { useAuthSession } from "@/lib/auth";
import { EmptyGraphState } from "./EmptyGraphState";
import { GraphCanvas } from "./GraphCanvas";
import { GraphSidebar } from "./GraphSidebar";
import { GraphStatsCards } from "./GraphStatsCards";
import type { KnowledgeFilterState } from "./GraphFilters";
import { NodeDetailPanel } from "./NodeDetailPanel";
import { RelationshipTable } from "./RelationshipTable";

const DEFAULT_FILTERS: KnowledgeFilterState = {
  query: "",
  nodeType: "all",
  edgeType: "all",
  limit: 250
};

export function KnowledgeGraphShell() {
  const { session, ready } = useAuthSession();
  const [filters, setFilters] = useState<KnowledgeFilterState>(DEFAULT_FILTERS);
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    const timer = window.setTimeout(() => {
      void load();
    }, filters.query ? 250 : 0);
    return () => window.clearTimeout(timer);
  }, [ready, filters.query, filters.nodeType, filters.edgeType, filters.limit]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const next = await fetchKnowledgeGraph({
        query: filters.query.trim(),
        nodeType: filters.nodeType,
        edgeType: filters.edgeType,
        limit: filters.limit
      });
      setGraph(next);
      setSelectedNode((current) => next.nodes.find((node) => node.id === current?.id) ?? next.nodes[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load knowledge graph.");
    } finally {
      setLoading(false);
    }
  }

  const empty = !loading && !error && (!graph || graph.nodes.length === 0);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Sơ đồ tri thức</h1>
          <p className="mt-1 text-sm text-slate-500">
            Khám phá mối liên hệ giữa email, lịch, task, người, dự án và deadline.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="focus-ring inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Refresh
        </button>
      </div>

      <div className="flex items-start gap-2 rounded-lg border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-900">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          Trang này phân tích sâu hơn phần Ngữ cảnh hôm nay trong Daily Briefing
          {session?.user.email ? ` cho ${session.user.email}.` : "."}
        </span>
      </div>

      <GraphStatsCards graph={graph} />

      {error ? (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      ) : null}

      {loading && !graph ? (
        <div className="flex min-h-[520px] items-center justify-center rounded-lg border border-line bg-white text-sm text-slate-500">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Loading graph...
        </div>
      ) : null}

      {empty ? <EmptyGraphState /> : null}

      {graph && graph.nodes.length ? (
        <div className="grid gap-4 xl:grid-cols-[16rem_minmax(0,1fr)_22rem]">
          <GraphSidebar filters={filters} onChange={setFilters} />
          <div className="min-w-0 space-y-4">
            <GraphCanvas graph={graph} selectedNode={selectedNode} onSelectNode={setSelectedNode} />
            <RelationshipTable nodes={graph.nodes} edges={graph.edges} />
          </div>
          <NodeDetailPanel node={selectedNode} nodes={graph.nodes} edges={graph.edges} />
        </div>
      ) : null}
    </div>
  );
}

"use client";

import { CalendarDays, CheckSquare, Mail, Network, UserRound } from "lucide-react";
import type { KnowledgeEdge, KnowledgeNode } from "@/lib/api";
import { compactLabel, metadataEntries, nodeColor, relatedEdges, relatedNodes } from "./graphUtils";

export function NodeDetailPanel({
  node,
  nodes,
  edges
}: {
  node: KnowledgeNode | null;
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}) {
  const connectedEdges = relatedEdges(node, edges);
  const connectedNodes = relatedNodes(node, nodes, edges);
  const grouped = {
    emails: connectedNodes.filter((item) => item.type === "EmailThread"),
    events: connectedNodes.filter((item) => item.type === "CalendarEvent"),
    tasks: connectedNodes.filter((item) => item.type === "Task"),
    projects: connectedNodes.filter((item) => item.type === "Project"),
    deadlines: connectedNodes.filter((item) => item.type === "Deadline")
  };

  return (
    <aside className="rounded-lg border border-line bg-white">
      <div className="border-b border-line p-4">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-brand" />
          <h2 className="text-sm font-semibold text-ink">Node details</h2>
        </div>
      </div>
      {!node ? (
        <div className="p-4 text-sm text-slate-500">Select a node in the graph to inspect related items and source metadata.</div>
      ) : (
        <div className="space-y-5 p-4">
          <div>
            <div className="mb-3 flex items-start gap-3">
              <div className="mt-1 h-3 w-3 rounded-full" style={{ backgroundColor: nodeColor(node.type) }} />
              <div className="min-w-0">
                <h3 className="break-words text-base font-semibold text-ink">{node.label}</h3>
                <p className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">{node.type}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Related" value={connectedEdges.length} />
              <Metric label="Sources" value={node.source_count ?? connectedEdges.length} />
            </div>
          </div>

          <RelatedSection title="Related emails" icon="mail" items={grouped.emails} />
          <RelatedSection title="Events" icon="calendar" items={grouped.events} />
          <RelatedSection title="Tasks" icon="task" items={grouped.tasks} />
          <RelatedSection title="Projects" icon="project" items={grouped.projects} />
          <RelatedSection title="Deadlines" icon="deadline" items={grouped.deadlines} />

          <div>
            <h3 className="text-sm font-semibold text-ink">Relationships</h3>
            <div className="mt-2 space-y-2">
              {connectedEdges.slice(0, 8).map((edge) => {
                const otherId = edge.source === node.id ? edge.target : edge.source;
                const other = nodes.find((item) => item.id === otherId);
                return (
                  <div key={edge.id} className="rounded-md bg-panel p-2 text-xs text-slate-600">
                    <span className="font-semibold text-slate-800">{edge.type}</span>
                    {other ? ` - ${compactLabel(other.label, 54)}` : null}
                  </div>
                );
              })}
              {!connectedEdges.length ? <p className="text-sm text-slate-500">No related edges in this view.</p> : null}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-ink">Metadata</h3>
            <div className="mt-2 divide-y divide-line rounded-md border border-line">
              {metadataEntries(node.metadata, 12).map(([key, value]) => (
                <div key={key} className="grid grid-cols-[7rem_minmax(0,1fr)] gap-2 px-3 py-2 text-xs">
                  <span className="font-medium text-slate-500">{key}</span>
                  <span className="break-words text-slate-700">{String(value)}</span>
                </div>
              ))}
              {!metadataEntries(node.metadata).length ? <div className="px-3 py-2 text-sm text-slate-500">No metadata available.</div> : null}
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-line bg-panel p-2">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-base font-semibold text-ink">{value}</div>
    </div>
  );
}

function RelatedSection({
  title,
  icon,
  items
}: {
  title: string;
  icon: "mail" | "calendar" | "task" | "project" | "deadline";
  items: KnowledgeNode[];
}) {
  const Icon = icon === "mail" ? Mail : icon === "calendar" ? CalendarDays : icon === "task" ? CheckSquare : icon === "project" ? Network : UserRound;
  if (!items.length) return null;
  return (
    <div>
      <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
        <Icon className="h-4 w-4 text-slate-500" />
        {title}
      </h3>
      <div className="mt-2 space-y-2">
        {items.slice(0, 6).map((item) => (
          <div key={item.id} className="rounded-md bg-panel p-2 text-sm text-slate-700">
            <div className="font-medium">{compactLabel(item.label, 58)}</div>
            {item.metadata?.from ? <div className="mt-1 text-xs text-slate-500">From: {String(item.metadata.from)}</div> : null}
            {item.metadata?.start ? <div className="mt-1 text-xs text-slate-500">Start: {String(item.metadata.start)}</div> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

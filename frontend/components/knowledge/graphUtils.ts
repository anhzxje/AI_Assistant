import type { KnowledgeEdge, KnowledgeNode } from "@/lib/api";

export const NODE_TYPES = [
  "Person",
  "EmailThread",
  "CalendarEvent",
  "Task",
  "Project",
  "Deadline",
  "Document",
  "Course",
  "Organization"
];

export const EDGE_TYPES = ["MENTIONS", "ASSIGNED_TO", "DEADLINE_FOR", "SCHEDULED_FOR", "RELATED_TO", "PART_OF", "SENT"];

export const NODE_COLORS: Record<string, string> = {
  Person: "#0f766e",
  EmailThread: "#2563eb",
  CalendarEvent: "#7c3aed",
  Task: "#b45309",
  Project: "#be123c",
  Deadline: "#c2410c",
  Document: "#475569",
  Course: "#4d7c0f",
  Organization: "#0891b2"
};

export function nodeColor(type: string) {
  return NODE_COLORS[type] ?? "#64748b";
}

export function relatedEdges(node: KnowledgeNode | null, edges: KnowledgeEdge[]) {
  if (!node) return [];
  return edges.filter((edge) => edge.source === node.id || edge.target === node.id);
}

export function relatedNodes(node: KnowledgeNode | null, nodes: KnowledgeNode[], edges: KnowledgeEdge[]) {
  if (!node) return [];
  const ids = new Set(
    relatedEdges(node, edges).map((edge) => {
      return edge.source === node.id ? edge.target : edge.source;
    })
  );
  return nodes.filter((item) => ids.has(item.id));
}

export function compactLabel(value: string, max = 42) {
  const text = String(value || "").trim();
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}...`;
}

export function metadataEntries(metadata: Record<string, any>, limit = 10) {
  return Object.entries(metadata ?? {})
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .slice(0, limit);
}

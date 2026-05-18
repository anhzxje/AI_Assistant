"use client";

import type { KnowledgeEdge, KnowledgeNode } from "@/lib/api";
import { compactLabel } from "./graphUtils";

export function RelationshipTable({ nodes, edges }: { nodes: KnowledgeNode[]; edges: KnowledgeEdge[] }) {
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  return (
    <section className="rounded-lg border border-line bg-white">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-sm font-semibold text-ink">Relationships</h2>
        <p className="text-xs text-slate-500">Filtered relationship list for audit and drill-down.</p>
      </div>
      <div className="max-h-80 overflow-auto">
        <table className="w-full min-w-[680px] text-left text-sm">
          <thead className="sticky top-0 bg-panel text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 font-semibold">Source</th>
              <th className="px-4 py-3 font-semibold">Type</th>
              <th className="px-4 py-3 font-semibold">Target</th>
              <th className="px-4 py-3 font-semibold">Weight</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {edges.slice(0, 80).map((edge) => (
              <tr key={edge.id} className="bg-white">
                <td className="px-4 py-3 text-slate-700">{compactLabel(nodeMap.get(edge.source)?.label ?? edge.source, 44)}</td>
                <td className="px-4 py-3">
                  <span className="rounded-md bg-panel px-2 py-1 text-xs font-semibold text-slate-700">{edge.type}</span>
                </td>
                <td className="px-4 py-3 text-slate-700">{compactLabel(nodeMap.get(edge.target)?.label ?? edge.target, 44)}</td>
                <td className="px-4 py-3 text-slate-500">{edge.weight ?? 1}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!edges.length ? <div className="p-4 text-sm text-slate-500">No relationships match the current filters.</div> : null}
      </div>
    </section>
  );
}

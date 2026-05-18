"use client";

import { useMemo } from "react";
import type { KnowledgeEdge, KnowledgeGraph, KnowledgeNode } from "@/lib/api";
import { compactLabel, nodeColor, relatedEdges } from "./graphUtils";

type LayoutNode = KnowledgeNode & {
  x: number;
  y: number;
  radius: number;
};

const VIEWPORT_W = 920;
const VIEWPORT_H = 560;

export function GraphCanvas({
  graph,
  selectedNode,
  onSelectNode
}: {
  graph: KnowledgeGraph;
  selectedNode: KnowledgeNode | null;
  onSelectNode: (node: KnowledgeNode) => void;
}) {
  const layout = useMemo(() => buildLayout(graph.nodes, graph.edges), [graph.nodes, graph.edges]);
  const selectedEdges = new Set(relatedEdges(selectedNode, graph.edges).map((edge) => edge.id));
  const selectedNeighborIds = new Set<string>();
  relatedEdges(selectedNode, graph.edges).forEach((edge) => {
    selectedNeighborIds.add(edge.source);
    selectedNeighborIds.add(edge.target);
  });

  return (
    <section className="rounded-lg border border-line bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-ink">Relationship map</h2>
          <p className="text-xs text-slate-500">Click a node to inspect its connected emails, tasks, projects, and deadlines.</p>
        </div>
        <Legend />
      </div>
      <div className="overflow-hidden">
        <svg className="h-[560px] w-full bg-slate-50" viewBox={`0 0 ${VIEWPORT_W} ${VIEWPORT_H}`} role="img" aria-label="Knowledge graph">
          <defs>
            <marker id="knowledge-arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L0,6 L9,3 z" fill="#94a3b8" />
            </marker>
          </defs>
          {graph.edges.map((edge) => {
            const source = layout.nodeMap.get(edge.source);
            const target = layout.nodeMap.get(edge.target);
            if (!source || !target) return null;
            const active = selectedEdges.has(edge.id);
            return (
              <g key={edge.id}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={active ? "#0f766e" : "#cbd5e1"}
                  strokeWidth={active ? 2.5 : 1.2}
                  markerEnd="url(#knowledge-arrow)"
                />
                {active ? (
                  <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 4} textAnchor="middle" className="fill-slate-600 text-[10px]">
                    {edge.type}
                  </text>
                ) : null}
              </g>
            );
          })}
          {layout.nodes.map((node) => {
            const active = selectedNode?.id === node.id;
            const neighbor = selectedNeighborIds.has(node.id);
            return (
              <g
                key={node.id}
                onClick={() => onSelectNode(node)}
                className="cursor-pointer"
                opacity={selectedNode && !active && !neighbor ? 0.38 : 1}
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.radius + (active ? 4 : 0)}
                  fill={active ? "#ecfeff" : "#ffffff"}
                  stroke={active ? "#0f766e" : nodeColor(node.type)}
                  strokeWidth={active ? 3 : 2}
                />
                <circle cx={node.x} cy={node.y} r={Math.max(5, node.radius - 4)} fill={nodeColor(node.type)} />
                <text x={node.x} y={node.y + node.radius + 14} textAnchor="middle" className="fill-slate-700 text-[11px] font-medium">
                  {compactLabel(node.label, 26)}
                </text>
                <text x={node.x} y={node.y + node.radius + 27} textAnchor="middle" className="fill-slate-400 text-[9px]">
                  {node.type}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </section>
  );
}

function Legend() {
  const items = [
    ["Person", "#0f766e"],
    ["Email", "#2563eb"],
    ["Task", "#b45309"],
    ["Project", "#be123c"],
    ["Deadline", "#c2410c"]
  ];
  return (
    <div className="flex flex-wrap gap-2 text-xs text-slate-600">
      {items.map(([label, color]) => (
        <span key={label} className="inline-flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
          {label}
        </span>
      ))}
    </div>
  );
}

function buildLayout(nodes: KnowledgeNode[], edges: KnowledgeEdge[]) {
  const capped = nodes.slice(0, 180);
  const nodeMap = new Map<string, LayoutNode>();
  const byType = new Map<string, KnowledgeNode[]>();
  capped.forEach((node) => {
    const items = byType.get(node.type) ?? [];
    items.push(node);
    byType.set(node.type, items);
  });

  const types = Array.from(byType.keys());
  const ringRadius = Math.min(VIEWPORT_W, VIEWPORT_H) * 0.33;
  const centerX = VIEWPORT_W / 2;
  const centerY = VIEWPORT_H / 2;
  let positioned: LayoutNode[] = [];

  types.forEach((type, typeIndex) => {
    const group = byType.get(type) ?? [];
    const groupAngle = (typeIndex / Math.max(types.length, 1)) * Math.PI * 2 - Math.PI / 2;
    const groupCenterX = centerX + Math.cos(groupAngle) * ringRadius * 0.55;
    const groupCenterY = centerY + Math.sin(groupAngle) * ringRadius * 0.55;
    group.forEach((node, index) => {
      const angle = (index / Math.max(group.length, 1)) * Math.PI * 2 + groupAngle;
      const localRadius = 30 + Math.sqrt(group.length) * 15 + (index % 3) * 10;
      const degree = edges.filter((edge) => edge.source === node.id || edge.target === node.id).length;
      const layoutNode = {
        ...node,
        x: clamp(groupCenterX + Math.cos(angle) * localRadius, 48, VIEWPORT_W - 48),
        y: clamp(groupCenterY + Math.sin(angle) * localRadius, 48, VIEWPORT_H - 54),
        radius: Math.min(18, 8 + Math.sqrt(Math.max(degree, node.source_count, 1)) * 2)
      };
      nodeMap.set(node.id, layoutNode);
      positioned.push(layoutNode);
    });
  });

  positioned = relax(positioned, edges);
  positioned.forEach((node) => nodeMap.set(node.id, node));
  return { nodes: positioned, nodeMap };
}

function relax(nodes: LayoutNode[], edges: KnowledgeEdge[]) {
  const idIndex = new Map(nodes.map((node, index) => [node.id, index]));
  const sim = nodes.map((node) => ({ ...node, vx: 0, vy: 0 }));
  const links = edges
    .map((edge) => [idIndex.get(edge.source), idIndex.get(edge.target)] as const)
    .filter((pair): pair is readonly [number, number] => pair[0] !== undefined && pair[1] !== undefined);

  for (let tick = 0; tick < 120; tick++) {
    for (let i = 0; i < sim.length; i++) {
      for (let j = i + 1; j < sim.length; j++) {
        const a = sim[i];
        const b = sim[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist2 = dx * dx + dy * dy + 0.01;
        const force = 900 / dist2;
        const dist = Math.sqrt(dist2);
        a.vx += (dx / dist) * force;
        a.vy += (dy / dist) * force;
        b.vx -= (dx / dist) * force;
        b.vy -= (dy / dist) * force;
      }
    }
    for (const [sourceIndex, targetIndex] of links) {
      const source = sim[sourceIndex];
      const target = sim[targetIndex];
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const dist = Math.sqrt(dx * dx + dy * dy) + 0.01;
      const pull = (dist - 86) * 0.012;
      source.vx += (dx / dist) * pull;
      source.vy += (dy / dist) * pull;
      target.vx -= (dx / dist) * pull;
      target.vy -= (dy / dist) * pull;
    }
    for (const node of sim) {
      node.vx += (VIEWPORT_W / 2 - node.x) * 0.001;
      node.vy += (VIEWPORT_H / 2 - node.y) * 0.001;
      node.vx *= 0.82;
      node.vy *= 0.82;
      node.x = clamp(node.x + node.vx, 36, VIEWPORT_W - 36);
      node.y = clamp(node.y + node.vy, 42, VIEWPORT_H - 48);
    }
  }
  return sim.map(({ vx, vy, ...node }) => node);
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

"use client";

import { Link2, Network, Shapes, Users } from "lucide-react";
import type { KnowledgeGraph } from "@/lib/api";

export function GraphStatsCards({ graph }: { graph: KnowledgeGraph | null }) {
  const nodeCounts = graph?.summary?.node_counts ?? {};
  const topType = Object.entries(nodeCounts).sort((a, b) => b[1] - a[1])[0];
  const stats = [
    { label: "Nodes", value: graph?.summary?.node_count ?? 0, icon: Network },
    { label: "Relationships", value: graph?.summary?.edge_count ?? 0, icon: Link2 },
    { label: "People", value: nodeCounts.Person ?? 0, icon: Users },
    { label: "Top type", value: topType ? `${topType[0]} ${topType[1]}` : "None", icon: Shapes }
  ];

  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <div key={stat.label} className="rounded-lg border border-line bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{stat.label}</p>
                <p className="mt-1 text-xl font-semibold text-ink">{stat.value}</p>
              </div>
              <div className="rounded-md bg-panel p-2 text-brand">
                <Icon className="h-5 w-5" />
              </div>
            </div>
          </div>
        );
      })}
    </section>
  );
}

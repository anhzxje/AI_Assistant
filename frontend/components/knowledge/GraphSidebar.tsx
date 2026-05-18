"use client";

import { SlidersHorizontal } from "lucide-react";
import type { KnowledgeFilterState } from "./GraphFilters";
import { GraphFilters } from "./GraphFilters";

export function GraphSidebar({
  filters,
  onChange
}: {
  filters: KnowledgeFilterState;
  onChange: (next: KnowledgeFilterState) => void;
}) {
  return (
    <aside className="rounded-lg border border-line bg-white p-4">
      <div className="mb-4 flex items-center gap-2">
        <SlidersHorizontal className="h-4 w-4 text-brand" />
        <h2 className="text-sm font-semibold text-ink">Filters</h2>
      </div>
      <GraphFilters filters={filters} onChange={onChange} />
    </aside>
  );
}

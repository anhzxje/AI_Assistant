"use client";

import { Filter, Search } from "lucide-react";
import { EDGE_TYPES, NODE_TYPES } from "./graphUtils";

export type KnowledgeFilterState = {
  query: string;
  nodeType: string;
  edgeType: string;
  limit: number;
};

export function GraphFilters({
  filters,
  onChange
}: {
  filters: KnowledgeFilterState;
  onChange: (next: KnowledgeFilterState) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500" htmlFor="knowledge-query">
          Search
        </label>
        <div className="mt-2 flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            id="knowledge-query"
            value={filters.query}
            onChange={(event) => onChange({ ...filters, query: event.target.value })}
            placeholder="Person, project, email..."
            className="w-full bg-transparent text-sm text-ink outline-none placeholder:text-slate-400"
          />
        </div>
      </div>

      <Select
        label="Node type"
        value={filters.nodeType}
        values={NODE_TYPES}
        onChange={(nodeType) => onChange({ ...filters, nodeType })}
      />
      <Select
        label="Edge type"
        value={filters.edgeType}
        values={EDGE_TYPES}
        onChange={(edgeType) => onChange({ ...filters, edgeType })}
      />

      <div>
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500" htmlFor="knowledge-limit">
          Limit
        </label>
        <select
          id="knowledge-limit"
          value={filters.limit}
          onChange={(event) => onChange({ ...filters, limit: Number(event.target.value) })}
          className="focus-ring mt-2 w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
        >
          {[100, 250, 500, 1000].map((value) => (
            <option key={value} value={value}>
              {value} nodes
            </option>
          ))}
        </select>
      </div>

      <div className="rounded-lg border border-line bg-panel p-3 text-xs text-slate-600">
        <div className="mb-2 flex items-center gap-2 font-semibold text-slate-700">
          <Filter className="h-4 w-4" />
          Scope
        </div>
        This page reads only the graph for the signed-in Lumi user.
      </div>
    </div>
  );
}

function Select({
  label,
  value,
  values,
  onChange
}: {
  label: string;
  value: string;
  values: string[];
  onChange: (value: string) => void;
}) {
  const id = `knowledge-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div>
      <label className="text-xs font-semibold uppercase tracking-wide text-slate-500" htmlFor={id}>
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="focus-ring mt-2 w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
      >
        <option value="all">All</option>
        {values.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
    </div>
  );
}

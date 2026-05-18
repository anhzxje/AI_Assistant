"use client";

import { Search, X } from "lucide-react";

export type SelectFilter = {
  id: string;
  label: string;
  value: string;
  options: Array<{ label: string; value: string }>;
  onChange: (value: string) => void;
};

type FilterBarProps = {
  searchValue?: string;
  searchPlaceholder?: string;
  onSearchChange?: (value: string) => void;
  onSearchSubmit?: () => void;
  filters?: SelectFilter[];
  onReset?: () => void;
};

export function FilterBar({
  searchValue,
  searchPlaceholder = "Search...",
  onSearchChange,
  onSearchSubmit,
  filters = [],
  onReset
}: FilterBarProps) {
  return (
    <div className="rounded-lg border border-line bg-white p-3">
      <div className="grid gap-2 md:grid-cols-[minmax(220px,1fr)_auto]">
        {onSearchChange ? (
          <label className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              value={searchValue ?? ""}
              onChange={(event) => onSearchChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") onSearchSubmit?.();
              }}
              className="focus-ring w-full rounded-md border border-line bg-white py-2 pl-9 pr-3 text-sm text-ink"
              placeholder={searchPlaceholder}
            />
          </label>
        ) : (
          <div />
        )}
        <div className="flex flex-wrap items-center gap-2">
          {filters.map((filter) => (
            <label key={filter.id} className="min-w-[150px]">
              <span className="sr-only">{filter.label}</span>
              <select
                value={filter.value}
                onChange={(event) => filter.onChange(event.target.value)}
                className="focus-ring w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-slate-700"
              >
                {filter.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          ))}
          {onSearchSubmit ? (
            <button
              type="button"
              onClick={onSearchSubmit}
              className="focus-ring rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
            >
              Apply
            </button>
          ) : null}
          {onReset ? (
            <button
              type="button"
              onClick={onReset}
              className="focus-ring inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <X className="h-4 w-4" />
              Reset
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

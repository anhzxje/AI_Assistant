"use client";

import { Loader2 } from "lucide-react";

export function MeetingPrepPanel({
  query,
  includeEmails,
  includeTasks,
  loading,
  onQueryChange,
  onIncludeEmailsChange,
  onIncludeTasksChange,
  onGenerate
}: {
  query: string;
  includeEmails: boolean;
  includeTasks: boolean;
  loading: boolean;
  onQueryChange: (value: string) => void;
  onIncludeEmailsChange: (value: boolean) => void;
  onIncludeTasksChange: (value: boolean) => void;
  onGenerate: () => void;
}) {
  return (
    <section className="rounded-lg border border-line bg-white p-4">
      <h2 className="text-base font-semibold text-ink">Chuẩn bị họp</h2>
      <textarea
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        rows={4}
        className="mt-3 w-full rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-cyan-700"
      />
      <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-700">
        <label className="inline-flex items-center gap-2">
          <input type="checkbox" checked={includeEmails} onChange={(event) => onIncludeEmailsChange(event.target.checked)} />
          Email liên quan
        </label>
        <label className="inline-flex items-center gap-2">
          <input type="checkbox" checked={includeTasks} onChange={(event) => onIncludeTasksChange(event.target.checked)} />
          Task liên quan
        </label>
      </div>
      <GenerateButton loading={loading} label="Tạo bản chuẩn bị" onClick={onGenerate} />
    </section>
  );
}

function GenerateButton({ loading, label, onClick }: { loading: boolean; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="focus-ring mt-4 inline-flex h-10 items-center gap-2 rounded-md bg-brand px-4 text-sm font-medium text-white hover:bg-cyan-800 disabled:bg-slate-300"
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
      {label}
    </button>
  );
}


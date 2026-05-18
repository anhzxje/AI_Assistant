"use client";

import type { ActionDraft } from "@/lib/api";

export function RecentDraftsPanel({ drafts, onSelect }: { drafts: ActionDraft[]; onSelect: (draft: ActionDraft) => void }) {
  return (
    <section className="rounded-lg border border-line bg-white p-4">
      <h2 className="text-sm font-semibold text-ink">Draft gần đây</h2>
      <div className="mt-3 space-y-2">
        {drafts.length ? (
          drafts.slice(0, 6).map((draft) => (
            <button key={draft.draft_id} type="button" onClick={() => onSelect(draft)} className="focus-ring block w-full rounded-md border border-line p-2 text-left text-sm hover:bg-slate-50">
              <div className="font-medium text-slate-800">{draft.title}</div>
              <div className="mt-1 text-xs text-slate-500">{draft.draft_type} | {new Date(draft.created_at).toLocaleString()}</div>
            </button>
          ))
        ) : (
          <p className="text-sm text-slate-500">Chưa có draft.</p>
        )}
      </div>
    </section>
  );
}


"use client";

import { Loader2 } from "lucide-react";

export function EmailDraftPanel({
  emailId,
  instruction,
  tone,
  loading,
  onEmailIdChange,
  onInstructionChange,
  onToneChange,
  onGenerate
}: {
  emailId: string;
  instruction: string;
  tone: "formal" | "friendly" | "short";
  loading: boolean;
  onEmailIdChange: (value: string) => void;
  onInstructionChange: (value: string) => void;
  onToneChange: (value: "formal" | "friendly" | "short") => void;
  onGenerate: () => void;
}) {
  return (
    <section className="rounded-lg border border-line bg-white p-4">
      <h2 className="text-base font-semibold text-ink">Email Draft</h2>
      <label className="mt-3 block text-sm font-medium text-slate-700">
        Email ID
        <input value={emailId} onChange={(event) => onEmailIdChange(event.target.value)} placeholder="Tùy chọn" className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm" />
      </label>
      <label className="mt-3 block text-sm font-medium text-slate-700">
        Yêu cầu
        <textarea value={instruction} onChange={(event) => onInstructionChange(event.target.value)} rows={3} className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm" />
      </label>
      <label className="mt-3 block text-sm font-medium text-slate-700">
        Tone
        <select value={tone} onChange={(event) => onToneChange(event.target.value as any)} className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm">
          <option value="formal">Formal</option>
          <option value="friendly">Friendly</option>
          <option value="short">Short</option>
        </select>
      </label>
      <button type="button" onClick={onGenerate} disabled={loading} className="focus-ring mt-4 inline-flex h-10 items-center gap-2 rounded-md bg-brand px-4 text-sm font-medium text-white hover:bg-cyan-800 disabled:bg-slate-300">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Tạo email draft
      </button>
    </section>
  );
}


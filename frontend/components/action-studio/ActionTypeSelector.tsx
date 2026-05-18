"use client";

import { FileText, Mail, Users } from "lucide-react";

export type ActionType = "meeting_prep" | "report" | "email_draft";

const ACTIONS = [
  { id: "meeting_prep", label: "Chuẩn bị họp", icon: Users },
  { id: "report", label: "Báo cáo", icon: FileText },
  { id: "email_draft", label: "Email Draft", icon: Mail }
] as const;

export function ActionTypeSelector({ value, onChange }: { value: ActionType; onChange: (value: ActionType) => void }) {
  return (
    <aside className="rounded-lg border border-line bg-white p-3">
      <div className="mb-3 text-xs font-semibold uppercase tracking-normal text-slate-400">Action</div>
      <div className="space-y-1">
        {ACTIONS.map((item) => {
          const Icon = item.icon;
          const active = item.id === value;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onChange(item.id)}
              className={`focus-ring flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium ${
                active ? "bg-cyan-50 text-cyan-900" : "text-slate-700 hover:bg-slate-50"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </button>
          );
        })}
      </div>
    </aside>
  );
}

"use client";

import type { DailyBriefing, SmartBriefing } from "@/lib/api";

export function ImportantEmailList({ smart, daily }: { smart: SmartBriefing | null; daily: DailyBriefing | null }) {
  const emails = smart?.important_emails?.length ? smart.important_emails : daily?.important_emails ?? [];
  return (
    <section className="rounded-lg border border-line bg-white p-5">
      <h3 className="text-sm font-semibold text-ink">Important Emails</h3>
      <div className="mt-3 space-y-3">
        {emails.map((message, index) => (
          <article key={message.message_id ?? index} className="rounded-md border border-line p-3">
            <div className="text-sm font-semibold text-ink">{message.subject || "(No subject)"}</div>
            <div className="mt-1 text-xs text-slate-500">{message.from} · {message.category ?? "email"}</div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{message.snippet}</p>
          </article>
        ))}
        {!emails.length ? <p className="text-sm text-slate-500">Không có email quan trọng sau khi lọc nhiễu.</p> : null}
      </div>
    </section>
  );
}

"use client";

import type { DailyBriefing, SmartBriefing } from "@/lib/api";

export function EventTimeline({ smart, daily }: { smart: SmartBriefing | null; daily: DailyBriefing | null }) {
  const events = smart?.upcoming_events?.length ? smart.upcoming_events : daily?.today_events ?? [];
  return (
    <section className="rounded-lg border border-line bg-white p-5">
      <h3 className="text-sm font-semibold text-ink">Event Timeline</h3>
      <div className="mt-3 space-y-3">
        {events.map((event, index) => (
          <article key={event.event_id ?? event.source_id ?? index} className="rounded-md border border-line p-3">
            <div className="text-sm font-semibold text-ink">{event.summary ?? event.title}</div>
            <div className="mt-1 text-xs text-slate-500">
              {event.start_time ?? event.start ?? "Cả ngày"} {event.location ? `· ${event.location}` : ""}
            </div>
          </article>
        ))}
        {!events.length ? <p className="text-sm text-slate-500">Không có sự kiện sắp tới trong dữ liệu hiện có.</p> : null}
      </div>
    </section>
  );
}

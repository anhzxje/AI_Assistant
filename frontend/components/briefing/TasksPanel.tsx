"use client";

import type { DailyBriefing } from "@/lib/api";
import { SyncStatsCard } from "./SyncStatsCard";

export function TasksPanel({ briefing }: { briefing: DailyBriefing | null }) {
  const tasks = briefing?.tasks ?? [];
  const high = tasks.filter((task) => task.priority === "high");
  const medium = tasks.filter((task) => task.priority !== "high");
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <SyncStatsCard label="Tasks" value={tasks.length} />
        <SyncStatsCard label="Ưu tiên cao" value={high.length} />
        <SyncStatsCard label="Từ email" value={briefing?.extracted_email_tasks.length ?? 0} />
      </div>
      <TaskGroup title="Ưu tiên cao" tasks={high} />
      <TaskGroup title="Các việc còn lại" tasks={medium} />
    </div>
  );
}

function TaskGroup({ title, tasks }: { title: string; tasks: Array<Record<string, any>> }) {
  return (
    <section className="rounded-lg border border-line bg-white p-5">
      <h2 className="text-sm font-semibold text-ink">{title}</h2>
      <div className="mt-3 space-y-3">
        {tasks.map((task, index) => (
          <article key={`${task.source_id ?? task.task_id ?? index}`} className="rounded-md border border-line p-3">
            <div className="text-sm font-medium text-ink">{task.title}</div>
            <div className="mt-1 text-xs text-slate-500">
              {task.priority ?? "medium"} {task.due_date ? `· hạn ${task.due_date}` : ""}
            </div>
          </article>
        ))}
        {!tasks.length ? <p className="text-sm text-slate-500">Không có mục nào.</p> : null}
      </div>
    </section>
  );
}

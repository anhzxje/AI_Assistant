"use client";

import type { SmartBriefing } from "@/lib/api";

export function ProjectUpdatePanel({ briefing }: { briefing: SmartBriefing | null }) {
  const projects = briefing?.project_updates ?? [];
  return (
    <section className="rounded-lg border border-line bg-white p-5">
      <h3 className="text-sm font-semibold text-ink">Projects</h3>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {projects.map((project, index) => (
          <div key={project.project_id ?? index} className="rounded-md border border-line p-3">
            <div className="text-sm font-semibold text-ink">{project.name}</div>
            <div className="mt-1 text-xs text-slate-500">{project.update_count ?? 0} mục liên quan</div>
            <div className="mt-2 flex flex-wrap gap-1">
              {(project.keywords ?? []).slice(0, 4).map((keyword: string) => (
                <span key={keyword} className="rounded-full bg-panel px-2 py-0.5 text-[11px] text-slate-600">
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        ))}
        {!projects.length ? <p className="text-sm text-slate-500">Chưa phát hiện cụm dự án rõ ràng.</p> : null}
      </div>
    </section>
  );
}

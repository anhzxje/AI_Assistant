"use client";

import { CalendarDays, Database, GitBranch, Inbox, LayoutDashboard, ListChecks, Settings, SlidersHorizontal, Workflow } from "lucide-react";

export type BriefingTab = "overview" | "gmail" | "calendar" | "tasks" | "projects" | "knowledge" | "sync" | "demo" | "settings";

const tabs: Array<{ id: BriefingTab; label: string; icon: typeof LayoutDashboard }> = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "gmail", label: "Gmail", icon: Inbox },
  { id: "calendar", label: "Calendar", icon: CalendarDays },
  { id: "tasks", label: "Tasks", icon: ListChecks },
  { id: "projects", label: "Projects", icon: Workflow },
  { id: "knowledge", label: "Knowledge", icon: GitBranch },
  { id: "sync", label: "Sync Center", icon: SlidersHorizontal },
  { id: "demo", label: "Dữ liệu mẫu", icon: Database },
  { id: "settings", label: "Settings", icon: Settings }
];

export function BriefingSidebar({
  activeTab,
  onChange
}: {
  activeTab: BriefingTab;
  onChange: (tab: BriefingTab) => void;
}) {
  return (
    <nav className="rounded-lg border border-line bg-white p-2 lg:w-56">
      <div className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onChange(tab.id)}
              className={`focus-ring inline-flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${
                active ? "bg-cyan-50 text-cyan-950" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

"use client";

import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  BriefcaseBusiness,
  Database,
  FileSearch,
  Inbox,
  ListChecks,
  ServerCog
} from "lucide-react";

export type AdminSection = "overview" | "sources" | "qa" | "feedback" | "jobs" | "knowledge";

type NavItem = {
  id: AdminSection;
  label: string;
  helper: string;
  icon: LucideIcon;
};

export const adminSections: NavItem[] = [
  { id: "overview", label: "Overview", helper: "Health and signals", icon: BarChart3 },
  { id: "sources", label: "Data Sources", helper: "Freshness and domains", icon: Database },
  { id: "qa", label: "QA & Eval", helper: "Quality gates", icon: ListChecks },
  { id: "feedback", label: "Feedback Inbox", helper: "Review and actions", icon: Inbox },
  { id: "jobs", label: "Jobs", helper: "Local maintenance", icon: ServerCog },
  { id: "knowledge", label: "Knowledge Admin", helper: "Documents and chunks", icon: FileSearch }
];

type AdminSidebarProps = {
  activeSection: AdminSection;
  onSectionChange: (section: AdminSection) => void;
};

export function AdminSidebar({ activeSection, onSectionChange }: AdminSidebarProps) {
  return (
    <aside className="border-b border-line bg-white lg:w-72 lg:border-b-0 lg:border-r">
      <div className="hidden border-b border-line px-4 py-4 lg:block">
        <div className="flex items-center gap-2 text-sm font-semibold text-ink">
          <BriefcaseBusiness className="h-4 w-4 text-brand" />
          Admin CMS
        </div>
        <p className="mt-1 text-xs text-slate-500">Decision workspace</p>
      </div>
      <nav className="flex gap-1 overflow-x-auto p-2 lg:block lg:space-y-1">
        {adminSections.map((item) => {
          const Icon = item.icon;
          const active = item.id === activeSection;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSectionChange(item.id)}
              className={`focus-ring flex min-w-[170px] items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition lg:w-full ${
                active ? "bg-brand text-white" : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="min-w-0">
                <span className="block truncate font-medium">{item.label}</span>
                <span className={active ? "block truncate text-xs text-cyan-50" : "block truncate text-xs text-slate-500"}>
                  {item.helper}
                </span>
              </span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}

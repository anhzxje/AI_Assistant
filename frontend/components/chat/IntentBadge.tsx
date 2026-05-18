import { BookOpen, Brain, CalendarDays, CheckSquare, HelpCircle, Mail, MessageSquareText, Search } from "lucide-react";

const intentConfig: Record<string, { label: string; className: string; icon: typeof MessageSquareText }> = {
  institutional_rag: {
    label: "Institutional",
    className: "border-cyan-200 bg-cyan-50 text-cyan-800",
    icon: Search
  },
  rag: {
    label: "Institutional",
    className: "border-cyan-200 bg-cyan-50 text-cyan-800",
    icon: Search
  },
  daily_briefing: {
    label: "Briefing",
    className: "border-amber-200 bg-amber-50 text-amber-800",
    icon: CalendarDays
  },
  personal_memory: {
    label: "Memory",
    className: "border-teal-200 bg-teal-50 text-teal-800",
    icon: Brain
  },
  tasks: {
    label: "Tasks",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
    icon: CheckSquare
  },
  gmail: {
    label: "Gmail",
    className: "border-sky-200 bg-sky-50 text-sky-800",
    icon: Mail
  },
  calendar: {
    label: "Calendar",
    className: "border-amber-200 bg-amber-50 text-amber-800",
    icon: CalendarDays
  },
  general_chat: {
    label: "General",
    className: "border-indigo-200 bg-indigo-50 text-indigo-800",
    icon: MessageSquareText
  },
  clarification: {
    label: "Clarify",
    className: "border-orange-200 bg-orange-50 text-orange-800",
    icon: HelpCircle
  },
  fallback: {
    label: "Fallback",
    className: "border-slate-200 bg-slate-50 text-slate-700",
    icon: BookOpen
  }
};

export function IntentBadge({ intent }: { intent?: string }) {
  const config = intentConfig[intent ?? ""] ?? {
    label: intent || "Assistant",
    className: "border-slate-200 bg-white text-slate-700",
    icon: MessageSquareText
  };
  const Icon = config.icon;

  return (
    <span className={`inline-flex h-6 max-w-full items-center gap-1 rounded-full border px-2 text-xs font-medium ${config.className}`}>
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span className="truncate">{config.label}</span>
    </span>
  );
}

"use client";

import type { ReactNode } from "react";
import type { AdminSection } from "./AdminSidebar";
import { AdminSidebar } from "./AdminSidebar";
import { AdminTopbar } from "./AdminTopbar";

type AdminShellProps = {
  title: string;
  subtitle?: string;
  activeSection: AdminSection;
  onSectionChange: (section: AdminSection) => void;
  loading?: boolean;
  onRefresh?: () => void;
  actions?: ReactNode;
  children: ReactNode;
};

export function AdminShell({
  title,
  subtitle,
  activeSection,
  onSectionChange,
  loading,
  onRefresh,
  actions,
  children
}: AdminShellProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-white shadow-sm">
      <div className="flex min-h-[calc(100vh-150px)] flex-col lg:flex-row">
        <AdminSidebar activeSection={activeSection} onSectionChange={onSectionChange} />
        <div className="min-w-0 flex-1 bg-panel">
          <AdminTopbar title={title} subtitle={subtitle} loading={loading} onRefresh={onRefresh} actions={actions} />
          <div className="space-y-5 p-3 sm:p-4">{children}</div>
        </div>
      </div>
    </div>
  );
}

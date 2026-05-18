"use client";

import Link from "next/link";
import { Network } from "lucide-react";

export function EmptyGraphState() {
  return (
    <div className="flex min-h-[520px] flex-col items-center justify-center rounded-lg border border-dashed border-line bg-white p-8 text-center">
      <div className="rounded-md bg-panel p-3 text-brand">
        <Network className="h-7 w-7" />
      </div>
      <h2 className="mt-4 text-base font-semibold text-ink">No graph data yet</h2>
      <p className="mt-2 max-w-md text-sm text-slate-500">
        Generate a smart briefing after Gmail or Calendar sync so Lumi can extract people, projects, tasks, deadlines, and source links.
      </p>
      <Link href="/briefing" className="focus-ring mt-4 rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-cyan-800">
        Open briefing
      </Link>
    </div>
  );
}

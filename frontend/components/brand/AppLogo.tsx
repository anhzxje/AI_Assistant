"use client";

import { BrandMark } from "./BrandMark";

export const APP_NAME = "Lumi";
export const APP_TAGLINE = "AI assistant for HUS knowledge, study, and productivity.";

export function AppLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <BrandMark className={compact ? "h-8 w-8" : "h-10 w-10"} />
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold tracking-normal text-ink sm:text-base">{APP_NAME}</div>
        {!compact ? <div className="truncate text-xs text-slate-500">{APP_TAGLINE}</div> : null}
      </div>
    </div>
  );
}

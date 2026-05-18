import type { ReactNode } from "react";

export function ResponsiveContainer({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <main className={`mx-auto max-w-7xl px-3 py-4 sm:px-4 sm:py-5 ${className}`}>{children}</main>;
}

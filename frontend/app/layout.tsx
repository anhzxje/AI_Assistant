import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppNav } from "@/components/layout/AppNav";
import { ResponsiveContainer } from "@/components/layout/ResponsiveContainer";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lumi",
  description: "AI assistant for HUS knowledge, study, and productivity."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <div className="min-h-screen">
          <AppNav />
          <ResponsiveContainer>{children}</ResponsiveContainer>
        </div>
      </body>
    </html>
  );
}

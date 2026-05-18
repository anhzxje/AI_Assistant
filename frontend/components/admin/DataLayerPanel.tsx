"use client";

import { Database, GitBranch, ShieldCheck } from "lucide-react";
import type { DataLayerSummary } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

type Props = {
  summary: DataLayerSummary | null;
};

export function DataLayerPanel({ summary }: Props) {
  const raw = summary?.layers.raw ?? {};
  const processed = summary?.layers.processed ?? {};
  const features = summary?.layers.features ?? {};
  const fileIngestion = summary?.file_ingestion ?? {};
  return (
    <section className="rounded-lg border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <Database className="mt-0.5 h-5 w-5 text-brand" />
        <div>
          <h2 className="text-base font-semibold text-ink">Data Layer Governance</h2>
          <p className="mt-1 text-sm text-slate-500">Raw, processed, feature, schema, version, and lineage status.</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <LayerTile label="Raw" value={raw.file_count} helper="Append-only source snapshots" />
        <LayerTile label="Processed" value={processed.documents ?? processed.file_count} helper="Cleaned normalized records" />
        <LayerTile label="Features" value={features.chunks ?? features.file_count} helper={`${features.qdrant_points ?? 0} vector points`} />
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <InfoLine icon={ShieldCheck} label="Schema registry" value={`${summary?.schema_registry.schema_count ?? 0} schemas`} />
        <InfoLine icon={GitBranch} label="Data version" value={String(summary?.latest_data_version.version ?? "unknown")} />
        <InfoLine icon={GitBranch} label="Lineage events" value={String(summary?.lineage.event_count ?? 0)} />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <LayerTile label="CSV" value={fileIngestion.csv?.rows ?? 0} helper={`${fileIngestion.csv?.count ?? 0} file(s), ${fileIngestion.csv?.status ?? "unknown"}`} />
        <LayerTile label="JSON" value={fileIngestion.json?.rows ?? 0} helper={`${fileIngestion.json?.count ?? 0} file(s), ${fileIngestion.json?.status ?? "unknown"}`} />
        <LayerTile label="Excel" value={fileIngestion.excel?.rows ?? 0} helper={`${fileIngestion.excel?.count ?? 0} file(s), ${fileIngestion.excel?.status ?? "unknown"}`} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={summary?.data_quality.status ?? "unknown"} />
        <StatusBadge value={summary?.governance.raw_immutable ? "raw immutable" : "raw policy missing"} tone="info" />
        <StatusBadge value="admin access controlled" tone="info" />
      </div>
    </section>
  );
}

function LayerTile({ label, value, helper }: { label: string; value: any; helper: string }) {
  return (
    <div className="rounded-md border border-line bg-panel p-3">
      <div className="text-xs font-medium uppercase tracking-normal text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-ink">{value ?? "-"}</div>
      <div className="mt-1 text-xs text-slate-500">{helper}</div>
    </div>
  );
}

function InfoLine({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm">
      <Icon className="h-4 w-4 text-brand" />
      <span className="text-slate-500">{label}</span>
      <span className="ml-auto font-semibold text-ink">{value}</span>
    </div>
  );
}

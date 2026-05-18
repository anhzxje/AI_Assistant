type MetricStripProps = {
  metrics: { label: string; value: number; suffix?: string }[];
};

export function MetricStrip({ metrics }: MetricStripProps) {
  const max = Math.max(...metrics.map((item) => item.value), 1);
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {metrics.map((item) => (
        <div key={item.label} className="rounded-lg border border-line bg-white p-4">
          <div className="text-sm text-slate-500">{item.label}</div>
          <div className="mt-2 text-xl font-semibold text-ink">
            {item.value}
            {item.suffix ?? ""}
          </div>
          <div className="mt-3 h-2 rounded bg-slate-100">
            <div className="h-2 rounded bg-accent" style={{ width: `${Math.max((item.value / max) * 100, 4)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

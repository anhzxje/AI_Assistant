type SimpleBarChartProps = {
  data: Record<string, number>;
  activeKey?: string;
};

export function SimpleBarChart({ data, activeKey }: SimpleBarChartProps) {
  const entries = Object.entries(data);
  const max = Math.max(...entries.map(([, value]) => value), 1);

  return (
    <div className="space-y-3">
      {entries.map(([label, value]) => {
        const width = `${Math.max((value / max) * 100, 3)}%`;
        const active = !activeKey || activeKey === label;
        return (
          <div key={label}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className={active ? "font-medium text-ink" : "text-slate-400"}>{label}</span>
              <span className="tabular-nums text-slate-500">{value}</span>
            </div>
            <div className="h-3 rounded bg-slate-100">
              <div
                className={active ? "h-3 rounded bg-brand" : "h-3 rounded bg-slate-300"}
                style={{ width }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

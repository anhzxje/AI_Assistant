"use client";

export type GmailRange = "7d" | "30d" | "90d" | "1y" | "all_recent";
export type CalendarRange = "7d" | "30d" | "90d" | "1y";

const rangeLabels: Record<string, string> = {
  "7d": "7 ngày",
  "30d": "30 ngày",
  "90d": "90 ngày",
  "1y": "1 năm",
  all_recent: "All recent"
};

export function SyncRangeSelector<T extends string>({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: T;
  options: T[];
  onChange: (value: T) => void;
}) {
  return (
    <label className="grid gap-2 text-sm font-medium text-slate-700">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        className="focus-ring h-10 rounded-md border border-line bg-white px-3 text-sm"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {rangeLabels[option] ?? option}
          </option>
        ))}
      </select>
    </label>
  );
}

export function MaxResultsSelector({
  value,
  onChange
}: {
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="grid gap-2 text-sm font-medium text-slate-700">
      Số email tối đa
      <select
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="focus-ring h-10 rounded-md border border-line bg-white px-3 text-sm"
      >
        {[10, 50, 100, 500, 1000, 2000].map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

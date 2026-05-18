"use client";

import { Loader2, RefreshCw } from "lucide-react";

const scenarios = [
  "student_clean",
  "student_noisy",
  "student_deadline_heavy",
  "lecturer",
  "admin_staff",
  "researcher",
  "thesis_student",
  "scholarship_case",
  "exam_schedule_case",
  "empty_new_user"
];

export function DemoScenarioPanel({
  scenario,
  syncing,
  onScenarioChange,
  onSync
}: {
  scenario: string;
  syncing: boolean;
  onScenarioChange: (value: string) => void;
  onSync: () => void;
}) {
  return (
    <section className="rounded-lg border border-dashed border-cyan-200 bg-cyan-50/60 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-cyan-950">Dữ liệu mẫu</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-cyan-800">
            Dùng fixture demo cho QA hoặc khi không muốn đọc dữ liệu Google. Phần này không tự chạy khi Gmail/Calendar đã kết nối.
          </p>
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-cyan-900">Local demo scenarios</span>
      </div>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="grid gap-2 text-sm font-medium text-cyan-950">
          Scenario
          <select value={scenario} onChange={(event) => onScenarioChange(event.target.value)} className="focus-ring h-10 rounded-md border border-cyan-200 bg-white px-3 text-sm">
            {scenarios.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={onSync}
          disabled={syncing}
          className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-cyan-900 px-4 text-sm font-medium text-white disabled:bg-slate-300"
        >
          {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Đồng bộ dữ liệu mẫu
        </button>
      </div>
    </section>
  );
}

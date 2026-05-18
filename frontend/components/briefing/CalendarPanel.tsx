"use client";

import { CalendarDays, Loader2, RefreshCw } from "lucide-react";
import type { CalendarInfo, DailyBriefing, SyncResponse } from "@/lib/api";
import type { CalendarRange } from "./SyncRangeSelector";
import { SyncStatsCard } from "./SyncStatsCard";

export function CalendarPanel({
  briefing,
  connected,
  range,
  startDate,
  endDate,
  calendars,
  selectedCalendarIds,
  includeAllCalendars,
  includeHolidays,
  includeCancelled,
  response,
  syncing,
  loadingCalendars,
  onRangeChange,
  onStartDateChange,
  onEndDateChange,
  onPreset,
  onSelectedCalendarIdsChange,
  onIncludeAllCalendarsChange,
  onIncludeHolidaysChange,
  onIncludeCancelledChange,
  onLoadCalendars,
  onSync
}: {
  briefing: DailyBriefing | null;
  connected: boolean;
  range: CalendarRange;
  startDate: string;
  endDate: string;
  calendars: CalendarInfo[];
  selectedCalendarIds: string[];
  includeAllCalendars: boolean;
  includeHolidays: boolean;
  includeCancelled: boolean;
  response: SyncResponse | null;
  syncing: boolean;
  loadingCalendars: boolean;
  onRangeChange: (value: CalendarRange) => void;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string) => void;
  onPreset: (days: number) => void;
  onSelectedCalendarIdsChange: (value: string[]) => void;
  onIncludeAllCalendarsChange: (value: boolean) => void;
  onIncludeHolidaysChange: (value: boolean) => void;
  onIncludeCancelledChange: (value: boolean) => void;
  onLoadCalendars: () => void;
  onSync: () => void;
}) {
  const events = response?.events ?? briefing?.today_events ?? [];
  const selectedCount = includeAllCalendars ? calendars.filter((calendar) => includeHolidays || !calendar.is_holiday).length : selectedCalendarIds.length;
  const dateRange = response?.date_range ?? response?.metadata?.date_range;

  function toggleCalendar(id: string) {
    if (selectedCalendarIds.includes(id)) {
      onSelectedCalendarIdsChange(selectedCalendarIds.filter((item) => item !== id));
    } else {
      onSelectedCalendarIdsChange([...selectedCalendarIds, id]);
    }
  }

  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-line bg-white p-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">Calendar</h2>
            <p className="mt-1 text-sm text-slate-500">Đồng bộ nhiều lịch Google trong khoảng ngày rõ ràng, chỉ với quyền đọc.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onLoadCalendars}
              disabled={loadingCalendars || !connected}
              className="focus-ring inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loadingCalendars ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarDays className="h-4 w-4" />}
              Tải danh sách lịch
            </button>
            <button
              type="button"
              onClick={onSync}
              disabled={syncing || !connected}
              className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-brand px-4 text-sm font-medium text-white hover:bg-cyan-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Đồng bộ Calendar
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <DateInput label="Từ ngày" value={startDate} onChange={onStartDateChange} />
              <DateInput label="Đến ngày" value={endDate} onChange={onEndDateChange} />
            </div>
            <div className="flex flex-wrap gap-2">
              <Preset label="Hôm nay" onClick={() => onPreset(0)} />
              <Preset label="7 ngày tới" onClick={() => onPreset(7)} />
              <Preset label="30 ngày tới" onClick={() => onPreset(30)} />
              <Preset label="90 ngày tới" onClick={() => onPreset(90)} />
              <Preset label="1 năm" onClick={() => onPreset(365)} />
            </div>
            <select
              value={range}
              onChange={(event) => onRangeChange(event.target.value as CalendarRange)}
              className="focus-ring w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
              aria-label="Fallback range"
            >
              <option value="7d">Fallback: 7 ngày</option>
              <option value="30d">Fallback: 30 ngày</option>
              <option value="90d">Fallback: 90 ngày</option>
              <option value="1y">Fallback: 1 năm</option>
            </select>
          </div>

          <div className="space-y-3 rounded-lg border border-line bg-panel p-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input type="checkbox" checked={includeAllCalendars} onChange={(event) => onIncludeAllCalendarsChange(event.target.checked)} />
              Đồng bộ tất cả lịch
            </label>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input type="checkbox" checked={includeHolidays} onChange={(event) => onIncludeHolidaysChange(event.target.checked)} />
              Bao gồm lịch ngày lễ
            </label>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input type="checkbox" checked={includeCancelled} onChange={(event) => onIncludeCancelledChange(event.target.checked)} />
              Bao gồm sự kiện đã huỷ
            </label>

            <div className="max-h-56 overflow-auto rounded-md border border-line bg-white">
              {calendars.map((calendar) => (
                <label key={calendar.id} className="flex items-start gap-2 border-b border-line px-3 py-2 text-sm last:border-b-0">
                  <input
                    type="checkbox"
                    disabled={includeAllCalendars}
                    checked={includeAllCalendars || selectedCalendarIds.includes(calendar.id)}
                    onChange={() => toggleCalendar(calendar.id)}
                    className="mt-1"
                  />
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-ink">
                      {calendar.summary} {calendar.primary ? "(primary)" : ""}
                    </span>
                    <span className="text-xs text-slate-500">
                      {calendar.is_classroom ? "Classroom/shared · " : ""}
                      {calendar.is_holiday ? "Ngày lễ · " : ""}
                      {calendar.accessRole}
                    </span>
                  </span>
                </label>
              ))}
              {!calendars.length ? <div className="p-3 text-sm text-slate-500">Chưa tải danh sách lịch.</div> : null}
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-4">
        <SyncStatsCard label="Lịch đã tải" value={calendars.length} />
        <SyncStatsCard label="Lịch đã chọn" value={selectedCount} />
        <SyncStatsCard label="Sự kiện sync" value={response?.events_count ?? response?.records_synced ?? 0} />
        <SyncStatsCard label="Hôm nay" value={response?.today_count ?? briefing?.today_events.length ?? 0} />
      </div>

      <section className="rounded-lg border border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-ink">Sự kiện đã đồng bộ</h3>
            <p className="mt-1 text-xs text-slate-500">
              {dateRange ? `${dateRange.start_date} đến ${dateRange.end_date}` : `${startDate} đến ${endDate}`}
            </p>
          </div>
          {response?.metadata?.synced_at ? <div className="text-xs text-slate-500">Lần cuối: {response.metadata.synced_at}</div> : null}
        </div>
        <div className="mt-3 space-y-3">
          {events.slice(0, 20).map((event) => (
            <article key={event.event_id ?? event.id} className="rounded-md border border-line p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-semibold text-ink">{event.summary}</div>
                <span className="rounded-md bg-panel px-2 py-1 text-xs text-slate-600">{event.calendar_name ?? "Calendar"}</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {event.start_date ?? event.start} {event.start_time ?? (event.is_all_day ? "Cả ngày" : "")}
                {event.location ? ` · ${event.location}` : ""} {event.status === "cancelled" ? " · Đã huỷ" : ""}
              </div>
              {event.description ? <p className="mt-2 text-sm leading-6 text-slate-700">{event.description}</p> : null}
            </article>
          ))}
          {!events.length ? (
            <p className="rounded-md bg-panel p-3 text-sm text-slate-600">
              Không có sự kiện nào trong khoảng ngày đã chọn. Hãy thử mở rộng khoảng thời gian hoặc chọn thêm lịch phụ.
            </p>
          ) : null}
        </div>
      </section>
    </div>
  );
}

function DateInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
      <input
        type="date"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="focus-ring mt-1 w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
      />
    </label>
  );
}

function Preset({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
      {label}
    </button>
  );
}

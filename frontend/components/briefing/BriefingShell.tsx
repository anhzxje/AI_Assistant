"use client";

import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  DailyBriefing,
  CalendarInfo,
  GoogleIntegrationStatus,
  KnowledgeSummary,
  SmartBriefing,
  SyncResponse,
  fetchKnowledgeSummary,
  fetchCalendarList,
  fetchDailyBriefing,
  fetchGoogleIntegrationStatus,
  fetchLatestSmartBriefing,
  generateSmartBriefing,
  syncCalendar,
  syncGmail
} from "@/lib/api";
import { useAuthSession } from "@/lib/auth";
import { BriefingOverview } from "./BriefingOverview";
import { BriefingSettingsPanel } from "./BriefingSettingsPanel";
import { BriefingSidebar, BriefingTab } from "./BriefingSidebar";
import { CalendarPanel } from "./CalendarPanel";
import { DemoScenarioPanel } from "./DemoScenarioPanel";
import { EventTimeline } from "./EventTimeline";
import { GmailPanel } from "./GmailPanel";
import { ImportantEmailList } from "./ImportantEmailList";
import { KnowledgeSummaryPanel } from "./KnowledgeSummaryPanel";
import { PriorityList } from "./PriorityList";
import { ProjectUpdatePanel } from "./ProjectUpdatePanel";
import { SmartReportCard } from "./SmartReportCard";
import { SuggestedActionPanel } from "./SuggestedActionPanel";
import { SyncCenterPanel } from "./SyncCenterPanel";
import { CalendarRange, GmailRange } from "./SyncRangeSelector";
import { TasksPanel } from "./TasksPanel";

export function BriefingShell() {
  const { session, ready } = useAuthSession();
  const userId = session?.user.user_id ?? "guest";
  const [activeTab, setActiveTab] = useState<BriefingTab>("overview");
  const [briefing, setBriefing] = useState<DailyBriefing | null>(null);
  const [smartBriefing, setSmartBriefing] = useState<SmartBriefing | null>(null);
  const [knowledgeSummary, setKnowledgeSummary] = useState<KnowledgeSummary | null>(null);
  const [status, setStatus] = useState<GoogleIntegrationStatus | null>(null);
  const [lastSync, setLastSync] = useState<SyncResponse[]>([]);
  const [gmailResponse, setGmailResponse] = useState<SyncResponse | null>(null);
  const [calendarResponse, setCalendarResponse] = useState<SyncResponse | null>(null);
  const [scenario, setScenario] = useState("student_clean");
  const [gmailRange, setGmailRange] = useState<GmailRange>("90d");
  const [gmailMaxResults, setGmailMaxResults] = useState(100);
  const [calendarRange, setCalendarRange] = useState<CalendarRange>("30d");
  const [calendarStartDate, setCalendarStartDate] = useState(todayIso());
  const [calendarEndDate, setCalendarEndDate] = useState(addDaysIso(30));
  const [calendars, setCalendars] = useState<CalendarInfo[]>([]);
  const [selectedCalendarIds, setSelectedCalendarIds] = useState<string[]>([]);
  const [includeAllCalendars, setIncludeAllCalendars] = useState(true);
  const [includeHolidays, setIncludeHolidays] = useState(false);
  const [includeCancelledCalendar, setIncludeCancelledCalendar] = useState(false);
  const [loadingCalendars, setLoadingCalendars] = useState(false);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<"gmail" | "calendar" | "both" | "mock" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gmailError, setGmailError] = useState<string | null>(null);
  const [calendarError, setCalendarError] = useState<string | null>(null);
  const [syncStartedAt, setSyncStartedAt] = useState<number | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    if (!ready) return;
    void load();
  }, [ready, userId]);

  useEffect(() => {
    if (!syncStartedAt || !syncing) return;
    const timer = window.setInterval(() => setElapsedMs(Date.now() - syncStartedAt), 250);
    return () => window.clearInterval(timer);
  }, [syncStartedAt, syncing]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [statusResponse, briefingResponse, smartResponse, knowledgeResponse] = await Promise.all([
        fetchGoogleIntegrationStatus(),
        fetchDailyBriefing(userId),
        fetchLatestSmartBriefing(),
        fetchKnowledgeSummary()
      ]);
      setStatus(statusResponse);
      setBriefing(briefingResponse);
      setSmartBriefing(smartResponse);
      setKnowledgeSummary(knowledgeResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được briefing.");
    } finally {
      setLoading(false);
    }
  }

  async function loadCalendars() {
    setLoadingCalendars(true);
    setCalendarError(null);
    try {
      const response = await fetchCalendarList();
      setCalendars(response.calendars);
      const defaults = response.calendars
        .filter((calendar) => (calendar.primary || calendar.selected || calendar.is_classroom) && !calendar.is_holiday)
        .map((calendar) => calendar.id);
      setSelectedCalendarIds(defaults);
    } catch (err) {
      setCalendarError(err instanceof Error ? err.message : "Không tải được danh sách lịch.");
    } finally {
      setLoadingCalendars(false);
    }
  }

  async function syncReal(kind: "gmail" | "calendar" | "both") {
    setSyncing(kind);
    setSyncStartedAt(Date.now());
    setElapsedMs(0);
    setError(null);
    setGmailError(null);
    setCalendarError(null);
    try {
      const results: SyncResponse[] = [];
      if (kind === "gmail" || kind === "both") {
        const result = await syncGmail({ userId, range: gmailRange, maxResults: gmailMaxResults, useMock: false });
        setGmailResponse(result);
        results.push(result);
      }
      if (kind === "calendar" || kind === "both") {
        const result = await syncCalendar({
          userId,
          range: calendarRange,
          startDate: calendarStartDate,
          endDate: calendarEndDate,
          calendarIds: includeAllCalendars ? [] : selectedCalendarIds,
          includeAllCalendars,
          includeHolidays,
          includeCancelled: includeCancelledCalendar,
          useMock: false
        });
        setCalendarResponse(result);
        results.push(result);
      }
      setLastSync(results);
      const smart = await generateSmartBriefing("today", false);
      setSmartBriefing(smart);
      setKnowledgeSummary(await fetchKnowledgeSummary());
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Không đồng bộ được dữ liệu Google.";
      if (kind === "gmail") setGmailError(message);
      else if (kind === "calendar") setCalendarError(message);
      else setError(message);
    } finally {
      setSyncing(null);
      setSyncStartedAt(null);
    }
  }

  async function syncMock() {
    setSyncing("mock");
    setSyncStartedAt(Date.now());
    setElapsedMs(0);
    setError(null);
    try {
      const results = await Promise.all([
        syncGmail({ userId, maxResults: 30, useMock: true, scenario }),
        syncCalendar({ userId, range: "30d", useMock: true, scenario })
      ]);
      setGmailResponse(results[0]);
      setCalendarResponse(results[1]);
      setLastSync(results);
      const smart = await generateSmartBriefing("today", true);
      setSmartBriefing(smart);
      setKnowledgeSummary(await fetchKnowledgeSummary());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không đồng bộ được dữ liệu mẫu.");
    } finally {
      setSyncing(null);
      setSyncStartedAt(null);
    }
  }

  const gmailSyncing = syncing === "gmail" || syncing === "both" || syncing === "mock";
  const calendarSyncing = syncing === "calendar" || syncing === "both" || syncing === "mock";
  const sourceMode = String(smartBriefing?.metadata?.source_mode ?? briefing?.metadata?.source_mode ?? "not_connected");
  const sourceBadge = useMemo(() => {
    if (sourceMode === "real") return "Nguồn: Google";
    if (sourceMode === "mock") return "Đang dùng dữ liệu mẫu";
    if (sourceMode === "mixed") return "Nguồn: Google + dữ liệu mẫu";
    return "Chưa kết nối";
  }, [sourceMode]);

  if (!ready || loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-lg border border-line bg-white text-sm text-slate-500">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Đang tải briefing...
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Daily Briefing</h1>
          <p className="mt-1 text-sm text-slate-500">
            Gmail và Calendar chỉ đọc cho <span className="font-medium">{session?.user.email ?? userId}</span>.
          </p>
          <div className="mt-2 inline-flex rounded-full border border-line bg-white px-3 py-1 text-xs font-medium text-slate-700">{sourceBadge}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void load()}
            className="focus-ring inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            Làm mới
          </button>
          <button
            type="button"
            onClick={() => void syncReal("both")}
            disabled={Boolean(syncing) || (!status?.gmail_connected && !status?.calendar_connected)}
            className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-brand px-3 text-sm font-medium text-white hover:bg-cyan-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {syncing === "both" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Tạo briefing
          </button>
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[14rem_minmax(0,1fr)]">
        <BriefingSidebar activeTab={activeTab} onChange={setActiveTab} />
        <main className="min-w-0">
          {activeTab === "overview" ? (
            <div className="space-y-5">
              <SmartReportCard briefing={smartBriefing} />
              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
                <div className="space-y-5">
                  <PriorityList briefing={smartBriefing} />
                  <ImportantEmailList smart={smartBriefing} daily={briefing} />
                  <EventTimeline smart={smartBriefing} daily={briefing} />
                </div>
                <div className="space-y-5">
                  <BriefingOverview briefing={briefing} status={status} lastSync={lastSync} />
                  <SuggestedActionPanel briefing={smartBriefing} />
                </div>
              </div>
            </div>
          ) : null}
          {activeTab === "gmail" ? (
            <GmailPanel
              briefing={briefing}
              connected={Boolean(status?.gmail_connected)}
              range={gmailRange}
              maxResults={gmailMaxResults}
              syncing={gmailSyncing}
              onRangeChange={setGmailRange}
              onMaxResultsChange={setGmailMaxResults}
              onSync={() => void syncReal("gmail")}
            />
          ) : null}
          {activeTab === "calendar" ? (
            <CalendarPanel
              briefing={briefing}
              connected={Boolean(status?.calendar_connected)}
              range={calendarRange}
              startDate={calendarStartDate}
              endDate={calendarEndDate}
              calendars={calendars}
              selectedCalendarIds={selectedCalendarIds}
              includeAllCalendars={includeAllCalendars}
              includeHolidays={includeHolidays}
              includeCancelled={includeCancelledCalendar}
              response={calendarResponse}
              syncing={calendarSyncing}
              loadingCalendars={loadingCalendars}
              onRangeChange={setCalendarRange}
              onStartDateChange={setCalendarStartDate}
              onEndDateChange={setCalendarEndDate}
              onPreset={(days) => {
                setCalendarStartDate(todayIso());
                setCalendarEndDate(addDaysIso(days));
                setCalendarRange(days <= 7 ? "7d" : days <= 30 ? "30d" : days <= 90 ? "90d" : "1y");
              }}
              onSelectedCalendarIdsChange={setSelectedCalendarIds}
              onIncludeAllCalendarsChange={setIncludeAllCalendars}
              onIncludeHolidaysChange={setIncludeHolidays}
              onIncludeCancelledChange={setIncludeCancelledCalendar}
              onLoadCalendars={() => void loadCalendars()}
              onSync={() => void syncReal("calendar")}
            />
          ) : null}
          {activeTab === "tasks" ? <TasksPanel briefing={briefing} /> : null}
          {activeTab === "projects" ? <ProjectUpdatePanel briefing={smartBriefing} /> : null}
          {activeTab === "knowledge" ? <KnowledgeSummaryPanel summary={knowledgeSummary} /> : null}
          {activeTab === "sync" ? (
            <SyncCenterPanel
              gmailSyncing={gmailSyncing}
              calendarSyncing={calendarSyncing}
              gmailResponse={gmailResponse}
              calendarResponse={calendarResponse}
              gmailError={gmailError}
              calendarError={calendarError}
              elapsedMs={elapsedMs}
            />
          ) : null}
          {activeTab === "demo" ? (
            <DemoScenarioPanel scenario={scenario} syncing={syncing === "mock"} onScenarioChange={setScenario} onSync={() => void syncMock()} />
          ) : null}
          {activeTab === "settings" ? <BriefingSettingsPanel session={session} status={status} /> : null}
        </main>
      </div>
    </div>
  );
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function addDaysIso(days: number) {
  const value = new Date();
  value.setDate(value.getDate() + days);
  return value.toISOString().slice(0, 10);
}

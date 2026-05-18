"use client";

import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import type { ActionDraft } from "@/lib/api";
import {
  createEmailDraft,
  createMeetingPrepDraft,
  createReportDraft,
  fetchRecentActionDrafts
} from "@/lib/api";
import { useAuthSession } from "@/lib/auth";
import { ActionTypeSelector, type ActionType } from "./ActionTypeSelector";
import { DraftPreview } from "./DraftPreview";
import { EmailDraftPanel } from "./EmailDraftPanel";
import { MeetingPrepPanel } from "./MeetingPrepPanel";
import { RecentDraftsPanel } from "./RecentDraftsPanel";
import { ReportDraftPanel } from "./ReportDraftPanel";
import { SourceContextPanel } from "./SourceContextPanel";

export function ActionStudioShell() {
  const { session, ready } = useAuthSession();
  const [actionType, setActionType] = useState<ActionType>("meeting_prep");
  const [draft, setDraft] = useState<ActionDraft | null>(null);
  const [recent, setRecent] = useState<ActionDraft[]>([]);
  const [loading, setLoading] = useState(false);
  const [recentLoading, setRecentLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [meetingQuery, setMeetingQuery] = useState("Chuẩn bị cho cuộc họp gần nhất");
  const [includeEmails, setIncludeEmails] = useState(true);
  const [includeTasks, setIncludeTasks] = useState(true);
  const [period, setPeriod] = useState<"today" | "7d" | "30d">("today");
  const [style, setStyle] = useState<"student" | "admin" | "research">("student");
  const [emailId, setEmailId] = useState("");
  const [emailInstruction, setEmailInstruction] = useState("viết phản hồi lịch sự");
  const [tone, setTone] = useState<"formal" | "friendly" | "short">("formal");

  useEffect(() => {
    if (!ready) return;
    void loadRecent();
  }, [ready]);

  async function loadRecent() {
    setRecentLoading(true);
    try {
      const response = await fetchRecentActionDrafts();
      setRecent(response.drafts);
      setDraft((current) => current ?? response.drafts[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được draft gần đây.");
    } finally {
      setRecentLoading(false);
    }
  }

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      let next: ActionDraft;
      if (actionType === "meeting_prep") {
        next = await createMeetingPrepDraft({ query: meetingQuery, includeEmails, includeTasks });
      } else if (actionType === "report") {
        next = await createReportDraft({ period, style });
      } else {
        next = await createEmailDraft({ emailId, instruction: emailInstruction, tone, language: "vi" });
      }
      setDraft(next);
      await loadRecent();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tạo được draft.");
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-lg border border-line bg-white text-sm text-slate-500">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Đang tải Action Studio...
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Action Studio</h1>
          <p className="mt-1 text-sm text-slate-500">
            Tạo bản nháp an toàn từ briefing, email, lịch, task và sơ đồ tri thức của {session?.user.email ?? "người dùng hiện tại"}.
          </p>
        </div>
        <button type="button" onClick={() => void loadRecent()} className="focus-ring inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50">
          <RefreshCw className="h-4 w-4" />
          Làm mới
        </button>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[15rem_minmax(0,1fr)_20rem]">
        <div className="space-y-4">
          <ActionTypeSelector value={actionType} onChange={setActionType} />
          {recentLoading ? (
            <div className="rounded-lg border border-line bg-white p-4 text-sm text-slate-500">Đang tải draft...</div>
          ) : (
            <RecentDraftsPanel drafts={recent} onSelect={setDraft} />
          )}
        </div>

        <main className="min-w-0 space-y-4">
          {actionType === "meeting_prep" ? (
            <MeetingPrepPanel
              query={meetingQuery}
              includeEmails={includeEmails}
              includeTasks={includeTasks}
              loading={loading}
              onQueryChange={setMeetingQuery}
              onIncludeEmailsChange={setIncludeEmails}
              onIncludeTasksChange={setIncludeTasks}
              onGenerate={() => void generate()}
            />
          ) : null}
          {actionType === "report" ? (
            <ReportDraftPanel period={period} style={style} loading={loading} onPeriodChange={setPeriod} onStyleChange={setStyle} onGenerate={() => void generate()} />
          ) : null}
          {actionType === "email_draft" ? (
            <EmailDraftPanel
              emailId={emailId}
              instruction={emailInstruction}
              tone={tone}
              loading={loading}
              onEmailIdChange={setEmailId}
              onInstructionChange={setEmailInstruction}
              onToneChange={setTone}
              onGenerate={() => void generate()}
            />
          ) : null}
          <DraftPreview draft={draft} />
        </main>

        <SourceContextPanel draft={draft} />
      </div>
    </div>
  );
}

"use client";

import { Bot, Clipboard, RotateCcw, UserRound, Volume2 } from "lucide-react";
import { BACKEND_URL } from "@/lib/api";
import type { ChatFeedbackState, ChatMessage, QualityMetadata } from "@/lib/types";
import { CitationCard } from "./CitationCard";
import { FeedbackControls } from "./FeedbackControls";
import { IntentBadge } from "./IntentBadge";
import { MarkdownMessage } from "./MarkdownMessage";
import { QualityBadge } from "./QualityBadge";

const clarificationPrompts = ["chương trình đào tạo", "giảng viên", "lịch hôm nay", "email", "task"];

function qualityFrom(message: ChatMessage): QualityMetadata | undefined {
  return message.metadata?.quality;
}

function generalLlmDisabled(message: ChatMessage) {
  if (message.intent !== "general_chat") return false;
  const mode = message.metadata?.general_llm_mode;
  return mode === "disabled" || mode === "llm_unavailable";
}

function briefingItems(content: string) {
  return content
    .split(/\r?\n/)
    .map((line) => line.replace(/^[-*]\s*/, "").trim())
    .filter((line) => line.length > 12)
    .slice(0, 4);
}

export function MessageBubble({
  message,
  sessionId,
  isLastAssistant,
  onFeedbackSaved,
  onCopy,
  onRetry,
  onQuickReply,
  userId,
  userRole
}: {
  message: ChatMessage;
  sessionId: string;
  isLastAssistant: boolean;
  onFeedbackSaved: (messageId: string, feedback: ChatFeedbackState) => void;
  onCopy: (content: string) => void;
  onRetry: () => void;
  onQuickReply: (content: string) => void;
  userId: string;
  userRole: string;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[88%] rounded-lg bg-brand px-4 py-3 text-sm leading-6 text-white shadow-sm sm:max-w-[72%]">
          <div className="whitespace-pre-wrap break-words">{message.content}</div>
          <div className="mt-2 text-right text-[11px] text-cyan-100">{new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
        </div>
      </div>
    );
  }

  const sources = (message.sources ?? []).filter((source) => source.usage !== "retrieval_debug" && source.used_in_answer !== false);
  const debugRetrieval = (message.metadata?.debug_retrieval ?? []) as typeof sources;
  const route = message.metadata?.route ?? [];
  const latency = message.metadata?.latency_ms;
  const items = message.intent === "daily_briefing" ? briefingItems(message.content) : [];
  const isAdmin = userRole === "admin";
  const isDraft = Boolean(message.metadata?.action_studio?.draft_only || message.actions?.includes("draft_only_no_write"));

  return (
    <div className="group flex items-start gap-3">
      <div className="mt-1 hidden h-8 w-8 shrink-0 items-center justify-center rounded-md border border-line bg-white text-brand sm:flex">
        <Bot className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1 text-sm font-semibold text-ink">
            <Bot className="h-4 w-4 sm:hidden" />
            Assistant
          </span>
          <IntentBadge intent={message.intent} />
          {isAdmin ? <QualityBadge quality={qualityFrom(message)} /> : null}
          {message.memoryUsed ? <span className="inline-flex h-6 items-center rounded-full border border-teal-200 bg-teal-50 px-2 text-xs font-medium text-teal-800">Memory</span> : null}
          {isDraft ? <span className="inline-flex h-6 items-center rounded-full border border-amber-200 bg-amber-50 px-2 text-xs font-medium text-amber-800">Bản nháp</span> : null}
          {isAdmin && typeof latency === "number" ? <span className="text-xs text-slate-500">{latency} ms</span> : null}
          {!isAdmin && sources.length ? (
            <span className="inline-flex h-6 items-center rounded-full border border-cyan-200 bg-cyan-50 px-2 text-xs font-medium text-cyan-800">
              Dựa trên dữ liệu HUS
            </span>
          ) : null}
        </div>

        {message.transcript ? (
          <div className="mb-3 rounded-lg border border-line bg-panel p-3 text-sm text-slate-700">
            <span className="font-medium text-ink">Transcript:</span> {message.transcript}
          </div>
        ) : null}

        <MarkdownMessage content={message.content} />

        {message.audioUrl ? (
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-line bg-white p-2">
            <Volume2 className="h-4 w-4 text-slate-500" />
            <audio className="w-full" controls src={`${BACKEND_URL}${message.audioUrl}`} />
          </div>
        ) : null}

        {generalLlmDisabled(message) ? (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
            Local LLM is disabled or unavailable, so general chat is running in fallback mode.
          </div>
        ) : null}

        {items.length ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {items.map((item) => (
              <div key={item} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
                {item}
              </div>
            ))}
          </div>
        ) : null}

        {message.intent === "clarification" ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {clarificationPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => onQuickReply(prompt)}
                className="focus-ring rounded-md border border-orange-200 bg-orange-50 px-3 py-1.5 text-sm text-orange-900 hover:bg-orange-100"
              >
                {prompt}
              </button>
            ))}
          </div>
        ) : null}

        {sources.length ? (
          <div className="mt-4 grid gap-3">
            {sources.map((source, index) => (
              <CitationCard
                key={`${source.chunk_id ?? source.event_id ?? source.message_id ?? source.source_url ?? index}`}
                source={source}
                index={source.citation_index ?? index + 1}
                isAdmin={isAdmin}
              />
            ))}
          </div>
        ) : null}

        {isAdmin && debugRetrieval.length ? (
          <details className="mt-3 rounded-lg border border-dashed border-line bg-white p-3 text-xs text-slate-600">
            <summary className="cursor-pointer font-medium text-slate-700">Xem nguồn truy xuất / Debug retrieval ({debugRetrieval.length})</summary>
            <div className="mt-3 grid gap-2">
              {debugRetrieval.map((source, index) => (
                <CitationCard
                  key={`debug-${source.chunk_id ?? source.source_url ?? index}`}
                  source={source}
                  index={source.citation_index ?? index + 1}
                  compact
                  isAdmin
                />
              ))}
            </div>
          </details>
        ) : null}

        <div className="mt-3 flex flex-wrap items-center gap-2 opacity-100 sm:opacity-0 sm:transition-opacity sm:group-hover:opacity-100">
          <button
            type="button"
            onClick={() => onCopy(message.content)}
            title="Copy answer"
            className="focus-ring inline-flex h-8 items-center gap-1 rounded-md border border-line bg-white px-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Clipboard className="h-3.5 w-3.5" />
            Copy
          </button>
          {isLastAssistant ? (
            <button
              type="button"
              onClick={onRetry}
              title="Retry last user message"
              className="focus-ring inline-flex h-8 items-center gap-1 rounded-md border border-line bg-white px-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Retry
            </button>
          ) : null}
        </div>

        <FeedbackControls message={message} sessionId={sessionId} userId={userId} onSaved={(feedback) => onFeedbackSaved(message.id, feedback)} />

        {isAdmin ? (
          <details className="mt-3 rounded-lg border border-line bg-panel p-3 text-xs text-slate-600">
            <summary className="cursor-pointer font-medium text-slate-700">Metadata</summary>
            <div className="mt-2 grid gap-2">
              <div>Route: {route.length ? route.join(" -> ") : "n/a"}</div>
              <pre className="max-h-60 overflow-auto whitespace-pre-wrap break-words rounded-md bg-white p-2 text-[11px] leading-5">
                {JSON.stringify(message.metadata ?? {}, null, 2)}
              </pre>
            </div>
          </details>
        ) : null}
      </div>
      <div className="mt-1 hidden h-8 w-8 shrink-0 items-center justify-center rounded-md border border-line bg-white text-slate-500 sm:flex">
        <UserRound className="h-4 w-4 opacity-0" />
      </div>
    </div>
  );
}

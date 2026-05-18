"use client";

import { useState } from "react";
import { Loader2, ThumbsDown, ThumbsUp } from "lucide-react";
import { submitFeedback, type FeedbackReason } from "@/lib/api";
import type { ChatFeedbackState, ChatMessage } from "@/lib/types";

const downvoteReasons: Array<{ value: FeedbackReason; label: string }> = [
  { value: "wrong_answer", label: "Wrong answer" },
  { value: "outdated_data", label: "Outdated data" },
  { value: "missing_source", label: "Missing source" },
  { value: "bad_citation", label: "Bad citation" },
  { value: "irrelevant_retrieval", label: "Irrelevant retrieval" },
  { value: "too_slow", label: "Too slow" },
  { value: "other", label: "Other" }
];

export function FeedbackControls({
  message,
  sessionId,
  userId,
  onSaved
}: {
  message: ChatMessage;
  sessionId: string;
  userId: string;
  onSaved: (feedback: ChatFeedbackState) => void;
}) {
  const [reason, setReason] = useState<FeedbackReason>("wrong_answer");
  const [correction, setCorrection] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function sendFeedback(rating: "up" | "down") {
    if (rating === "down" && !expanded) {
      setExpanded(true);
      return;
    }
    setSaving(true);
    setNotice(null);
    try {
      await submitFeedback({
        userId,
        sessionId,
        messageId: message.metadata?.assistant_message_id ?? message.id,
        query: message.query ?? "",
        answer: message.content,
        intent: message.intent ?? "fallback",
        route: message.metadata?.route ?? [],
        sources: message.sources ?? [],
        rating,
        reason: rating === "up" ? "other" : reason,
        correction,
        diagnostics: message.metadata?.feedback_diagnostics ?? message.metadata?.quality
      });
      const saved = { rating, reason: rating === "up" ? "other" : reason, status: "saved" } as ChatFeedbackState;
      onSaved(saved);
      setNotice("Feedback saved");
      setExpanded(false);
      setCorrection("");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Feedback failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-3 rounded-lg border border-line bg-white p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-normal text-slate-500">Feedback</span>
        <button
          type="button"
          onClick={() => sendFeedback("up")}
          disabled={saving}
          title="Helpful"
          className="focus-ring inline-flex h-8 items-center gap-1 rounded-md border border-line px-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <ThumbsUp className="h-4 w-4" />
          <span aria-hidden="true">👍</span>
        </button>
        <button
          type="button"
          onClick={() => sendFeedback("down")}
          disabled={saving}
          title="Needs review"
          className="focus-ring inline-flex h-8 items-center gap-1 rounded-md border border-line px-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <ThumbsDown className="h-4 w-4" />
          <span aria-hidden="true">👎</span>
        </button>
        {saving ? <Loader2 className="h-4 w-4 animate-spin text-slate-500" /> : null}
        {notice ? <span className="text-xs text-slate-500">{notice}</span> : null}
      </div>
      {expanded ? (
        <div className="mt-3 grid gap-2">
          <select
            value={reason}
            onChange={(event) => setReason(event.target.value as FeedbackReason)}
            className="focus-ring h-10 rounded-md border border-line bg-white px-3 text-sm text-ink"
          >
            {downvoteReasons.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <textarea
            value={correction}
            onChange={(event) => setCorrection(event.target.value)}
            rows={3}
            className="focus-ring resize-none rounded-md border border-line px-3 py-2 text-sm leading-6 text-ink"
            placeholder="Optional correction..."
          />
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => sendFeedback("down")}
              disabled={saving}
              className="focus-ring inline-flex h-9 items-center rounded-md bg-slate-800 px-3 text-sm font-medium text-white hover:bg-slate-900 disabled:bg-slate-300"
            >
              Submit feedback
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

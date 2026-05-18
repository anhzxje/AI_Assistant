"use client";

import { useEffect, useMemo, useRef } from "react";
import { Loader2 } from "lucide-react";
import { APP_NAME, AppLogo } from "@/components/brand/AppLogo";
import type { ChatFeedbackState, ChatMessage } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";
import { SuggestedPrompts } from "./SuggestedPrompts";

export function MessageList({
  messages,
  sessionId,
  loading,
  loadingLabel,
  onPrompt,
  onFeedbackSaved,
  onCopy,
  onRetry,
  userId,
  userRole
}: {
  messages: ChatMessage[];
  sessionId: string;
  loading: boolean;
  loadingLabel?: string;
  onPrompt: (prompt: string) => void;
  onFeedbackSaved: (messageId: string, feedback: ChatFeedbackState) => void;
  onCopy: (content: string) => void;
  onRetry: () => void;
  userId: string;
  userRole: string;
}) {
  const endRef = useRef<HTMLDivElement | null>(null);
  const lastAssistantId = useMemo(() => [...messages].reverse().find((message) => message.role === "assistant")?.id, [messages]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, loading]);

  if (!messages.length) {
    return (
      <div className="flex min-h-full items-center justify-center p-5">
        <div className="w-full max-w-2xl">
          <div className="mb-5">
            <AppLogo />
            <p className="mt-3 text-sm text-slate-500">
              Hỏi về dữ liệu HUS, lịch cá nhân, ghi nhớ, tác vụ hoặc trò chuyện tổng quát với {APP_NAME}.
            </p>
          </div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-500">Gợi ý bắt đầu</div>
          <SuggestedPrompts onSelect={onPrompt} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 sm:p-5">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          sessionId={sessionId}
          isLastAssistant={message.id === lastAssistantId}
          onFeedbackSaved={onFeedbackSaved}
          onCopy={onCopy}
          onRetry={onRetry}
          onQuickReply={onPrompt}
          userId={userId}
          userRole={userRole}
        />
      ))}
      {loading ? (
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          {loadingLabel ?? "Đang tổng hợp câu trả lời..."}
        </div>
      ) : null}
      <div ref={endRef} />
    </div>
  );
}

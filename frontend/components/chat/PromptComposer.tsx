"use client";

import type { KeyboardEvent } from "react";
import { useEffect, useRef } from "react";
import { Loader2, RotateCcw, Send } from "lucide-react";
import { VoiceRecorderButton } from "./VoiceRecorderButton";

export function PromptComposer({
  value,
  onChange,
  onSubmit,
  onRetry,
  canRetry,
  loading,
  voiceLoading,
  voiceStatus,
  useMockGoogle,
  onUseMockGoogleChange,
  showMockGoogleToggle,
  onVoiceAudio,
  onVoiceError
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onRetry: () => void;
  canRetry: boolean;
  loading: boolean;
  voiceLoading: boolean;
  voiceStatus?: string | null;
  useMockGoogle: boolean;
  onUseMockGoogleChange: (value: boolean) => void;
  showMockGoogleToggle?: boolean;
  onVoiceAudio: (audio: Blob, voiceMode?: string) => Promise<void> | void;
  onVoiceError: (message: string) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 176)}px`;
  }, [value]);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  }

  const busy = loading || voiceLoading;

  return (
    <div className="sticky bottom-0 border-t border-line bg-white/95 px-3 py-3 backdrop-blur sm:px-5">
      <div className="mx-auto w-full max-w-3xl rounded-xl border border-line bg-white p-2 shadow-sm">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          className="focus-ring max-h-44 min-h-12 w-full resize-none overflow-y-auto rounded-lg border-0 px-3 py-2 text-sm leading-6 text-ink placeholder:text-slate-400 focus:ring-0 focus:ring-offset-0"
          placeholder="Nhập tin nhắn cho Lumi..."
          disabled={busy}
        />

        <div className="mt-2 flex min-w-0 items-center justify-between gap-2 border-t border-slate-100 pt-2">
          {showMockGoogleToggle ? (
            <label className="inline-flex min-w-0 items-center gap-2 truncate text-xs font-medium text-slate-600">
              <input
                type="checkbox"
                checked={useMockGoogle}
                onChange={(event) => onUseMockGoogleChange(event.target.checked)}
                className="h-4 w-4 shrink-0 rounded border-line text-brand"
              />
              <span className="truncate">Dùng dữ liệu mẫu</span>
            </label>
          ) : (
            <span className="text-xs text-slate-400">Dùng Google nếu đã kết nối</span>
          )}

          <div className="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              onClick={onRetry}
              disabled={!canRetry || busy}
              title="Retry last message"
              className="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md border border-line bg-white text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
            <VoiceRecorderButton disabled={loading} processing={voiceLoading} onAudioReady={onVoiceAudio} onError={onVoiceError} />
            <button
              type="button"
              onClick={onSubmit}
              disabled={busy || !value.trim()}
              title="Send"
              className="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md bg-brand text-white hover:bg-cyan-800 disabled:cursor-not-allowed disabled:bg-slate-300 sm:w-auto sm:px-3"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              <span className="ml-2 hidden text-sm font-medium sm:inline">Send</span>
            </button>
          </div>
        </div>
      </div>
      <div className="mx-auto mt-2 flex max-w-3xl items-center justify-between gap-2 px-1 text-[11px] text-slate-400">
        <span>Enter để gửi, Shift+Enter để xuống dòng.</span>
        {voiceStatus ? <span className="truncate text-slate-500">{voiceStatus}</span> : null}
      </div>
    </div>
  );
}

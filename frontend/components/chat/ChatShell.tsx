"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle } from "lucide-react";
import { BACKEND_URL, postAssistantChat, postVoiceChat, type AssistantChatResponse, type VoiceChatResponse } from "@/lib/api";
import { setStoredAuth, useAuthSession } from "@/lib/auth";
import {
  clearActiveConversationId,
  loadActiveConversationId,
  loadConversationsForUser,
  saveActiveConversationId,
  saveConversationsForUser
} from "@/lib/storage";
import { isMeaningfulConversation, type ChatFeedbackState, type ChatMessage, type Conversation } from "@/lib/types";
import { AssistantStatePanel } from "./AssistantStatePanel";
import { ConversationSidebar } from "./ConversationSidebar";
import { MessageList } from "./MessageList";
import { PromptComposer } from "./PromptComposer";

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}_${crypto.randomUUID()}`;
  }
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function nowIso() {
  return new Date().toISOString();
}

function titleFrom(content: string) {
  const compact = content.replace(/\s+/g, " ").trim();
  if (!compact) return "New chat";
  return compact.length > 42 ? `${compact.slice(0, 42)}...` : compact;
}

function createConversation(sessionId?: string): Conversation {
  const timestamp = nowIso();
  return {
    id: createId("conversation"),
    title: "New chat",
    sessionId: sessionId ?? createId("session"),
    createdAt: timestamp,
    updatedAt: timestamp,
    messages: []
  };
}

function responseToMessage(response: AssistantChatResponse, query: string, extra?: Partial<ChatMessage>): ChatMessage {
  return {
    id: response.metadata?.assistant_message_id ?? createId("assistant"),
    role: "assistant",
    content: response.answer,
    createdAt: nowIso(),
    intent: response.intent,
    sources: response.sources,
    actions: response.actions,
    metadata: response.metadata,
    memoryUsed: response.memory_used,
    query,
    ...extra
  };
}

function voiceToAssistantResponse(voice: VoiceChatResponse): AssistantChatResponse {
  return {
    answer: voice.answer,
    intent: voice.intent,
    sources: voice.sources ?? [],
    actions: voice.actions?.length ? voice.actions : ["voice_chat"],
    memory_used: Boolean(voice.memory_used ?? voice.metadata?.memory_used),
    metadata: {
      latency_ms: voice.metadata?.voice_latency_ms ?? voice.metadata?.latency_ms ?? 0,
      route: voice.metadata?.route ?? ["voice_chat"],
      voice: voice.metadata,
      spoken_answer: voice.spoken_answer,
      quality: voice.metadata?.quality,
      general_llm_mode: voice.metadata?.general_llm_mode
    }
  };
}

export function ChatShell() {
  const { session, ready } = useAuthSession();
  const userId = session?.user.user_id ?? "guest";
  const userRole = session?.user.role ?? "user";
  const isAdmin = userRole === "admin";
  const [hydrated, setHydrated] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [useMockGoogle, setUseMockGoogle] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [voiceStatus, setVoiceStatus] = useState<string | null>(null);
  const [lastAudioUrl, setLastAudioUrl] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!ready) return;
    setHydrated(false);
    const loaded = loadConversationsForUser(userId);
    const conversationsForUser = loaded.length ? loaded : [createConversation()];
    const storedActiveId = loadActiveConversationId(userId);
    const activeId =
      storedActiveId && conversationsForUser.some((item) => item.id === storedActiveId && !item.archived)
        ? storedActiveId
        : conversationsForUser.find((item) => !item.archived)?.id ?? conversationsForUser[0].id;
    setConversations(conversationsForUser);
    setActiveConversationId(activeId);
    setInput("");
    setError(null);
    setNotice(null);
    setSidebarOpen(false);
    setHydrated(true);
  }, [ready, userId]);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId),
    [conversations, activeConversationId]
  );

  const lastAssistantMessage = useMemo(
    () => [...(activeConversation?.messages ?? [])].reverse().find((message) => message.role === "assistant"),
    [activeConversation?.messages]
  );

  const canRetry = Boolean(activeConversation?.messages.some((message) => message.role === "user"));

  useEffect(() => {
    if (!hydrated) return;
    saveConversationsForUser(userId, conversations);
    if (activeConversationId) {
      saveActiveConversationId(userId, activeConversationId);
    }
  }, [activeConversationId, conversations, hydrated, userId]);

  function updateConversation(conversationId: string, updater: (conversation: Conversation) => Conversation) {
    setConversations((current) => current.map((conversation) => (conversation.id === conversationId ? updater(conversation) : conversation)));
  }

  function appendMessage(conversationId: string, message: ChatMessage, titleSeed?: string) {
    updateConversation(conversationId, (conversation) => ({
      ...conversation,
      title: conversation.messages.length === 0 && titleSeed ? titleFrom(titleSeed) : conversation.title,
      updatedAt: nowIso(),
      messages: [...conversation.messages, message]
    }));
  }

  function newChat() {
    const conversation = createConversation();
    setConversations((current) => [conversation, ...current.filter(isMeaningfulConversation)]);
    setActiveConversationId(conversation.id);
    setInput("");
    setError(null);
    setNotice(null);
    setSidebarOpen(false);
  }

  function renameConversation(conversationId: string) {
    const conversation = conversations.find((item) => item.id === conversationId);
    if (!conversation) return;
    const title = window.prompt("Rename conversation", conversation.title);
    const nextTitle = title?.trim();
    if (!nextTitle) return;
    updateConversation(conversationId, (current) => ({ ...current, title: nextTitle, updatedAt: nowIso() }));
  }

  function deleteConversation(conversationId: string) {
    const conversation = conversations.find((item) => item.id === conversationId);
    if (!conversation) return;
    const confirmed = window.confirm(`Delete "${conversation.title}"? This only removes this conversation for ${session?.user.email ?? userId}.`);
    if (!confirmed) return;
    const remaining = conversations.filter((item) => item.id !== conversationId && isMeaningfulConversation(item));
    const nextConversations = remaining.length ? remaining : [createConversation()];
    const nextActive =
      activeConversationId === conversationId
        ? nextConversations.find((item) => !item.archived)?.id ?? nextConversations[0].id
        : activeConversationId;
    setConversations(nextConversations);
    setActiveConversationId(nextActive);
    setNotice("Conversation deleted");
  }

  function archiveConversation(conversationId: string) {
    const conversation = conversations.find((item) => item.id === conversationId);
    if (!conversation || !isMeaningfulConversation(conversation)) return;
    const wasActive = activeConversationId === conversationId;
    const next = conversations.map((conversation) =>
      conversation.id === conversationId ? { ...conversation, archived: true, updatedAt: nowIso() } : conversation
    );
    const visible = next.filter((conversation) => !conversation.archived);
    const finalConversations = visible.length ? next : [createConversation(), ...next];
    setConversations(finalConversations);
    if (wasActive) {
      setActiveConversationId(finalConversations.find((conversation) => !conversation.archived)?.id ?? finalConversations[0].id);
    }
    setNotice("Conversation archived");
  }

  function restoreConversation(conversationId: string) {
    updateConversation(conversationId, (conversation) => ({ ...conversation, archived: false, updatedAt: nowIso() }));
    setActiveConversationId(conversationId);
    setNotice("Conversation restored");
  }

  function exportConversation(conversationId: string) {
    const conversation = conversations.find((item) => item.id === conversationId);
    if (!conversation || !isMeaningfulConversation(conversation)) return;
    const markdown = [
      `# ${conversation.title}`,
      "",
      `- User: ${session?.user.email ?? userId}`,
      `- Conversation: ${conversation.id}`,
      `- Session: ${conversation.sessionId}`,
      "",
      ...conversation.messages.map((message) => `## ${message.role === "user" ? "User" : "Assistant"}\n\n${message.content}`)
    ].join("\n");
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${conversation.title.replace(/[^a-zA-Z0-9_-]+/g, "-").slice(0, 48) || "conversation"}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function logout() {
    setStoredAuth(null);
    clearActiveConversationId(userId);
    setConversations([]);
    setActiveConversationId("");
    setInput("");
    window.location.href = "/login";
  }

  async function submitText(content = input) {
    const text = content.trim();
    if (!text || !activeConversation || loading || voiceLoading) return;
    const conversationId = activeConversation.id;
    const sessionId = activeConversation.sessionId;
    const userMessage: ChatMessage = {
      id: createId("user"),
      role: "user",
      content: text,
      createdAt: nowIso()
    };

    appendMessage(conversationId, userMessage, text);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const response = await postAssistantChat({
        message: text,
        userId,
        role: userRole,
        sessionId,
        includeMemory: true,
        useMockGoogle
      });
      appendMessage(conversationId, responseToMessage(response, text));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Chat request failed";
      setError(message);
      appendMessage(conversationId, {
        id: createId("assistant"),
        role: "assistant",
        content: message,
        createdAt: nowIso(),
        intent: "fallback",
        sources: [],
        actions: [],
        metadata: { latency_ms: 0, route: ["frontend_error"] },
        query: text,
        error: message
      });
    } finally {
      setLoading(false);
    }
  }

  async function submitVoice(audio: Blob, voiceMode = "push_to_talk") {
    if (!activeConversation || loading || voiceLoading) return;
    const conversationId = activeConversation.id;
    const sessionId = activeConversation.sessionId;
    setVoiceLoading(true);
    setVoiceStatus("Đang xử lý giọng nói...");
    setError(null);
    try {
      const voice = await postVoiceChat({
        audio,
        userId,
        sessionId,
        includeMemory: true,
        useMockGoogle,
        voiceMode
      });
      setVoiceStatus(`Đã nghe: ${voice.transcript}`);
      const transcript = voice.transcript || "Voice message";
      appendMessage(
        conversationId,
        {
          id: createId("user"),
          role: "user",
          content: transcript,
          transcript,
          createdAt: nowIso()
        },
        transcript
      );
      const assistant = responseToMessage(voiceToAssistantResponse(voice), transcript, {
        transcript,
        audioUrl: voice.audio_url
      });
      appendMessage(conversationId, assistant);
      if (voice.audio_url) {
        setVoiceStatus("Đang phát câu trả lời...");
        setLastAudioUrl(`${BACKEND_URL}${voice.audio_url}`);
        const player = new Audio(`${BACKEND_URL}${voice.audio_url}`);
        player.onended = () => setVoiceStatus(null);
        void player.play().catch(() => {
          setVoiceStatus("Nhấn phát lại để nghe câu trả lời.");
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice request failed");
      setVoiceStatus(null);
    } finally {
      setVoiceLoading(false);
    }
  }

  function replayVoice() {
    if (!lastAudioUrl) return;
    const player = new Audio(lastAudioUrl);
    setVoiceStatus("Đang phát lại...");
    player.onended = () => setVoiceStatus(null);
    void player.play().catch(() => setVoiceStatus("Trình duyệt chặn tự phát âm thanh."));
  }

  function retryLastUserMessage() {
    const lastUser = [...(activeConversation?.messages ?? [])].reverse().find((message) => message.role === "user");
    if (lastUser) {
      void submitText(lastUser.content);
    }
  }

  async function copyAnswer(content: string) {
    try {
      await navigator.clipboard.writeText(content);
      setNotice("Copied");
    } catch {
      setNotice("Copy failed");
    }
  }

  function saveFeedback(messageId: string, feedback: ChatFeedbackState) {
    if (!activeConversation) return;
    updateConversation(activeConversation.id, (conversation) => ({
      ...conversation,
      messages: conversation.messages.map((message) => (message.id === messageId ? { ...message, feedback } : message))
    }));
  }

  if (!hydrated) {
    return <div className="min-h-[620px] rounded-lg border border-line bg-white p-5 text-sm text-slate-500">Loading chat...</div>;
  }

  return (
    <div className="h-[calc(100vh-104px)] min-h-[640px] overflow-hidden rounded-lg border border-line bg-white shadow-sm">
      <div className="flex h-full min-h-0">
        <ConversationSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          mobileOpen={sidebarOpen}
          onMobileOpenChange={setSidebarOpen}
          onSelect={setActiveConversationId}
          onNew={newChat}
          onRename={renameConversation}
          onDelete={deleteConversation}
          onArchive={archiveConversation}
          onRestore={restoreConversation}
          onExport={exportConversation}
          onLogout={logout}
          user={session?.user ?? null}
        />

        <section className="flex min-w-0 flex-1 flex-col bg-panel">
          <div className="flex min-h-14 items-center justify-between gap-3 border-b border-line bg-white px-4">
            <div className="min-w-0">
              <h1 className="truncate text-base font-semibold text-ink">{activeConversation?.title ?? "New chat"}</h1>
              {isAdmin ? (
                <div className="truncate text-xs text-slate-500">
                  {session?.user.email ?? "guest"} · {userId} ·{" "}
                  {activeConversation?.sessionId ? `session ${activeConversation.sessionId.slice(0, 8)}` : "session pending"}
                </div>
              ) : null}
            </div>
            {notice ? <div className="rounded-full border border-line bg-panel px-3 py-1 text-xs font-medium text-slate-600">{notice}</div> : null}
            {voiceStatus ? (
              <button
                type="button"
                onClick={replayVoice}
                className="rounded-full border border-line bg-panel px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
              >
                {voiceStatus}
              </button>
            ) : null}
          </div>

          {error ? (
            <div className="mx-4 mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span className="break-words">{error}</span>
            </div>
          ) : null}

          <div className="min-h-0 flex-1 overflow-y-auto">
            <MessageList
              messages={activeConversation?.messages ?? []}
              sessionId={activeConversation?.sessionId ?? ""}
              loading={loading || voiceLoading}
              loadingLabel={voiceLoading ? "Đang tạo giọng nói..." : "Đang tìm nguồn và tổng hợp câu trả lời..."}
              onPrompt={(prompt) => void submitText(prompt)}
              onFeedbackSaved={saveFeedback}
              onCopy={copyAnswer}
              onRetry={retryLastUserMessage}
              userId={userId}
              userRole={userRole}
            />
          </div>

          <PromptComposer
            value={input}
            onChange={setInput}
            onSubmit={() => void submitText()}
            onRetry={retryLastUserMessage}
            canRetry={canRetry}
            loading={loading}
            voiceLoading={voiceLoading}
            voiceStatus={voiceStatus}
            useMockGoogle={useMockGoogle}
            onUseMockGoogleChange={setUseMockGoogle}
            showMockGoogleToggle={isAdmin}
            onVoiceAudio={submitVoice}
            onVoiceError={setError}
          />
        </section>

        {isAdmin ? <AssistantStatePanel conversation={activeConversation} lastAssistantMessage={lastAssistantMessage} user={session?.user ?? null} /> : null}
      </div>
    </div>
  );
}

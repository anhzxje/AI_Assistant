import type { AssistantChatResponse, AssistantSource, FeedbackReason } from "./api";

export type ChatRole = "user" | "assistant";

export type ChatFeedbackState = {
  rating: "up" | "down";
  reason?: FeedbackReason;
  status?: string;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  intent?: string;
  sources?: AssistantSource[];
  actions?: string[];
  metadata?: AssistantChatResponse["metadata"];
  memoryUsed?: boolean;
  query?: string;
  transcript?: string;
  audioUrl?: string;
  feedback?: ChatFeedbackState;
  error?: string;
};

export type Conversation = {
  id: string;
  title: string;
  sessionId: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
  archived?: boolean;
};

export const DEFAULT_CONVERSATION_TITLES = new Set(["New chat", "Chat mới", "Cuộc trò chuyện mới"]);

export function hasCustomConversationTitle(conversation: Conversation): boolean {
  const title = conversation.title.trim();
  return Boolean(title) && !DEFAULT_CONVERSATION_TITLES.has(title);
}

export function isMeaningfulConversation(conversation: Conversation): boolean {
  const hasUserMessage = conversation.messages.some((message) => message.role === "user");
  const hasAnyMessage = conversation.messages.length > 0;
  return hasUserMessage || hasCustomConversationTitle(conversation) || Boolean(conversation.archived && hasAnyMessage);
}

export type QualityMetadata = {
  quality_score?: number;
  issues?: string[];
  requires_admin_review?: boolean;
};

export const CHAT_STORAGE_KEYS = {
  scopedConversations: "omni:conversations",
  scopedActiveConversation: "omni:activeConversation",
  scopedSession: "omni:session"
} as const;

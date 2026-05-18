"use client";

import { CHAT_STORAGE_KEYS, type Conversation } from "./types";

export function scopedUserId(userId?: string | null) {
  return (userId || "guest").replace(/[^a-zA-Z0-9._-]/g, "_");
}

export function conversationStorageKey(userId?: string | null) {
  return `${CHAT_STORAGE_KEYS.scopedConversations}:${scopedUserId(userId)}`;
}

export function activeConversationStorageKey(userId?: string | null) {
  return `${CHAT_STORAGE_KEYS.scopedActiveConversation}:${scopedUserId(userId)}`;
}

export function sessionStorageKey(userId: string | null | undefined, conversationId: string) {
  return `${CHAT_STORAGE_KEYS.scopedSession}:${scopedUserId(userId)}:${conversationId}`;
}

export function loadConversationsForUser(userId?: string | null): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(conversationStorageKey(userId));
    const parsed = raw ? (JSON.parse(raw) as Conversation[]) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    window.localStorage.removeItem(conversationStorageKey(userId));
    return [];
  }
}

export function saveConversationsForUser(userId: string | null | undefined, conversations: Conversation[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(conversationStorageKey(userId), JSON.stringify(conversations));
  for (const conversation of conversations) {
    window.localStorage.setItem(sessionStorageKey(userId, conversation.id), conversation.sessionId);
  }
}

export function loadActiveConversationId(userId?: string | null) {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(activeConversationStorageKey(userId));
}

export function saveActiveConversationId(userId: string | null | undefined, conversationId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(activeConversationStorageKey(userId), conversationId);
}

export function clearActiveConversationId(userId?: string | null) {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(activeConversationStorageKey(userId));
}

export function clearActiveConversationForAllKnownUsers() {
  if (typeof window === "undefined") return;
  for (let index = window.localStorage.length - 1; index >= 0; index -= 1) {
    const key = window.localStorage.key(index);
    if (key?.startsWith(`${CHAT_STORAGE_KEYS.scopedActiveConversation}:`)) {
      window.localStorage.removeItem(key);
    }
  }
}

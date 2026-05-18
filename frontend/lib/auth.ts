"use client";

import { useEffect, useState } from "react";
import { clearActiveConversationId } from "./storage";

export type AuthUser = {
  user_id: string;
  email: string;
  display_name: string;
  role: "user" | "admin" | string;
  role_label: string;
  disabled?: boolean;
};

export type AuthSession = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export const AUTH_STORAGE_KEY = "omni_auth_session";

export function getStoredAuth(): AuthSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthSession) : null;
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

export function setStoredAuth(session: AuthSession | null) {
  if (typeof window === "undefined") return;
  if (!session) {
    const previous = getStoredAuth();
    if (previous?.user.user_id) {
      clearActiveConversationId(previous.user.user_id);
    }
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  } else {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
  }
  window.dispatchEvent(new Event("omni-auth-changed"));
}

export function currentUserId() {
  return getStoredAuth()?.user.user_id ?? "guest";
}

export function isAdminSession(session: AuthSession | null) {
  return session?.user.role === "admin";
}

export function useAuthSession() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    function refresh() {
      setSession(getStoredAuth());
      setReady(true);
    }
    refresh();
    window.addEventListener("storage", refresh);
    window.addEventListener("omni-auth-changed", refresh);
    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener("omni-auth-changed", refresh);
    };
  }, []);

  return { session, ready, isAdmin: isAdminSession(session) };
}

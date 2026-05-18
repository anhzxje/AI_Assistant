"""Sanitize personal context before showing it in Action Studio drafts."""

from __future__ import annotations

import re
from email.utils import parseaddr
from typing import Any

from backend.app.services.formatting.calendar_formatter import clean_event_title, clean_text, format_calendar_event_for_user


EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
TAG_RE = re.compile(r"<[^>]+>")
FORWARDED_RE = re.compile(r"-{2,}\s*Forwarded message\s*-{2,}.*", re.IGNORECASE | re.DOTALL)
NOISY_PHRASES = (
    "Cài đặt thông báo",
    "Cai dat thong bao",
    "Forwarded message",
    "accounts.google",
    "classroom.google",
    "google.com/url",
)


def sanitize_event(event: dict[str, Any] | None, *, role: str = "user") -> dict[str, Any] | None:
    if not event:
        return None
    cleaned = {
        "event_id": event.get("event_id"),
        "summary": clean_event_title(str(event.get("summary") or "")),
        "start_date": event.get("start_date"),
        "start_time": event.get("start_time"),
        "end_date": event.get("end_date"),
        "end_time": event.get("end_time"),
        "location": clean_text(str(event.get("location") or "")),
        "description": sanitize_text(event.get("description"), limit=220),
        "category": event.get("category"),
        "status": event.get("status"),
        "is_all_day": event.get("is_all_day"),
        "html_link": event.get("html_link"),
    }
    cleaned["display"] = format_calendar_event_for_user(cleaned, role=role)
    return cleaned


def sanitize_person(person: dict[str, Any]) -> dict[str, Any]:
    raw = str(person.get("name") or person.get("email") or "")
    name, email = parseaddr(raw)
    if not email:
        email = str(person.get("email") or "")
    display = name or raw or email.split("@")[0]
    display = EMAIL_RE.sub("", display)
    display = re.sub(r"\([^)]*@[^)]*\)", "", display)
    display = clean_text(display)
    return {"name": display or "Người liên quan", "email": email.lower() if email else "", "role": person.get("role")}


def sanitize_email(message: dict[str, Any]) -> dict[str, Any]:
    name, email = parseaddr(str(message.get("from") or ""))
    sender = clean_text(name or EMAIL_RE.sub("", str(message.get("from") or ""))) or email.split("@")[0]
    return {
        "message_id": message.get("message_id"),
        "thread_id": message.get("thread_id"),
        "subject": sanitize_text(message.get("subject"), limit=120),
        "sender": sender,
        "date": message.get("date"),
        "snippet": sanitize_text(message.get("snippet") or message.get("body"), limit=180),
        "is_unread": message.get("is_unread"),
    }


def sanitize_task(task: dict[str, Any]) -> dict[str, Any]:
    title = sanitize_text(task.get("title") or task.get("source_text"), limit=160)
    return {
        "task_id": task.get("task_id") or task.get("source_id"),
        "title": title or "Task cần xử lý",
        "due_date": task.get("due_date"),
        "priority": task.get("priority") or "medium",
    }


def sanitize_project(project: dict[str, Any] | None) -> dict[str, Any] | None:
    if not project:
        return None
    name = sanitize_text(project.get("name"), limit=80)
    if not name or is_bad_project_name(name):
        return None
    return {**project, "name": name}


def sanitize_text(value: Any, *, limit: int = 240) -> str:
    text = str(value or "")
    text = FORWARDED_RE.sub("", text)
    text = TAG_RE.sub(" ", text)
    text = URL_RE.sub("", text)
    text = EMAIL_RE.sub("", text)
    for phrase in NOISY_PHRASES:
        text = text.replace(phrase, "")
    text = re.sub(r"\[[^\]]*@[^]]+\]", "", text)
    text = clean_text(text)
    if len(text) <= limit:
        return text
    boundary = text.rfind(" ", 0, limit)
    return text[: boundary if boundary > 80 else limit].rstrip(" ,;:.") + "..."


def is_bad_project_name(value: str) -> bool:
    normalized = re.sub(r"[^a-z0-9à-ỹ]+", " ", value.lower()).strip()
    blocked = {
        "google",
        "https",
        "google https",
        "accounts google",
        "classroom google",
        "notification",
        "thông báo",
        "cài đặt",
        "lớp học",
        "forwarded message",
        "no reply",
    }
    return normalized in blocked or any(term in normalized for term in ("https", "accounts google", "classroom google"))


def contains_noisy_artifacts(text: str) -> bool:
    lowered = text.lower()
    return bool(EMAIL_RE.search(text)) or any(phrase.lower() in lowered for phrase in NOISY_PHRASES) or "google https" in lowered


def keyword_tokens(*values: str) -> set[str]:
    tokens: set[str] = set()
    stop = {
        "cuoc",
        "cuộc",
        "hop",
        "họp",
        "hom",
        "hôm",
        "nay",
        "ngay",
        "mai",
        "chuan",
        "chuẩn",
        "bi",
        "bị",
        "cho",
        "lich",
        "lịch",
        "thi",
        "exam",
        "kiem",
        "kiểm",
        "tra",
    }
    for value in values:
        for token in re.findall(r"[A-Za-zÀ-ỹ0-9]{3,}", (value or "").lower()):
            if token not in stop:
                tokens.add(token)
    return tokens

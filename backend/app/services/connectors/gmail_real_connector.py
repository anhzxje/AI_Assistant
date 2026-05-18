"""Real Gmail read-only adapter."""

from __future__ import annotations

import base64
from email.header import decode_header
from email.utils import parsedate_to_datetime
import re
from typing import Any

import httpx

from backend.app.services.integrations.google_token_store import GoogleTokenStore

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def sync_gmail_readonly(
    user_id: str,
    max_results: int = 100,
    token_store: GoogleTokenStore | None = None,
    query: str = "newer_than:90d",
    include_spam_trash: bool = False,
) -> list[dict[str, Any]]:
    store = token_store or GoogleTokenStore()
    token = store.refresh_if_needed(user_id, "gmail")
    if not token or not token.get("access_token"):
        raise RuntimeError("gmail_not_connected")

    capped_max = min(max(1, max_results), 2000)
    messages: list[dict[str, Any]] = []
    page_token = None
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    with httpx.Client(timeout=httpx.Timeout(20.0, connect=10.0)) as client:
        while len(messages) < capped_max:
            listed_response = client.get(
                f"{GMAIL_API_BASE}/messages",
                headers=headers,
                params={
                    "maxResults": min(500, capped_max - len(messages)),
                    "q": query or None,
                    "includeSpamTrash": str(include_spam_trash).lower(),
                    "pageToken": page_token,
                },
            )
            listed_response.raise_for_status()
            listed = listed_response.json()
            for item in listed.get("messages", []):
                raw_response = client.get(
                    f"{GMAIL_API_BASE}/messages/{item['id']}",
                    headers=headers,
                    params={"format": "full"},
                )
                raw_response.raise_for_status()
                messages.append(normalize_gmail_api_message(raw_response.json()))
                if len(messages) >= capped_max:
                    break
            page_token = listed.get("nextPageToken")
            if not page_token:
                break
    return messages


def normalize_gmail_api_message(message: dict[str, Any]) -> dict[str, Any]:
    payload = message.get("payload") or {}
    headers = {str(item.get("name", "")).lower(): decode_mime_header(str(item.get("value") or "")) for item in payload.get("headers", [])}
    labels = message.get("labelIds") or []
    body = extract_plain_text(payload)
    subject = headers.get("subject", "")
    snippet = message.get("snippet") or body[:240]
    attachments = attachment_filenames(payload)
    return {
        "id": message.get("id"),
        "thread_id": message.get("threadId"),
        "labelIds": labels,
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "cc": headers.get("cc", ""),
        "subject": subject,
        "snippet": snippet,
        "internalDate": message.get("internalDate"),
        "body": body,
        "body_text": body,
        "body_html": "",
        "date": normalize_date(headers.get("date", "")),
        "labels": labels,
        "is_unread": "UNREAD" in labels,
        "is_important": "IMPORTANT" in labels,
        "is_starred": "STARRED" in labels,
        "has_attachment": bool(attachments),
        "attachments": attachments,
        "category": classify_email(subject, snippet, labels),
        "priority_hint": priority_hint(subject, snippet, labels),
        "expected_task": expected_task(subject, snippet),
    }


def extract_plain_text(payload: dict[str, Any]) -> str:
    parts = payload.get("parts") or []
    if not parts:
        if payload.get("mimeType") and payload.get("mimeType") != "text/plain":
            return ""
        return decode_body((payload.get("body") or {}).get("data"), charset=part_charset(payload))
    for part in parts:
        if part.get("mimeType") == "text/plain":
            text = decode_body((part.get("body") or {}).get("data"), charset=part_charset(part))
            if text:
                return text
        if str(part.get("mimeType") or "").startswith("multipart/"):
            nested = extract_plain_text(part)
            if nested:
                return nested
    return ""


def decode_body(data: str | None, *, charset: str = "utf-8") -> str:
    if not data:
        return ""
    raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    candidates = [charset, "utf-8", "utf-16", "windows-1258", "latin-1"]
    for encoding in dict.fromkeys([item for item in candidates if item]):
        try:
            return raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    try:
        return raw.decode("utf-8")
    except Exception:
        return ""


def part_charset(payload: dict[str, Any]) -> str:
    for header in payload.get("headers") or []:
        if str(header.get("name") or "").lower() == "content-type":
            match = re.search(r"charset=[\"']?([^\"';\\s]+)", str(header.get("value") or ""), flags=re.IGNORECASE)
            if match:
                return match.group(1)
    return "utf-8"


def attachment_filenames(payload: dict[str, Any]) -> list[str]:
    filenames: list[str] = []
    for part in payload.get("parts") or []:
        filename = decode_mime_header(str(part.get("filename") or "").strip())
        if filename:
            filenames.append(filename)
        filenames.extend(attachment_filenames(part))
    return filenames


def decode_mime_header(value: str) -> str:
    if not value:
        return ""
    try:
        chunks = []
        for part, encoding in decode_header(value):
            if isinstance(part, bytes):
                chunks.append(part.decode(encoding or "utf-8"))
            else:
                chunks.append(part)
        return "".join(chunks)
    except Exception:
        return value


def normalize_date(value: str) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).isoformat()
    except Exception:
        return value


def classify_email(subject: str, snippet: str, labels: list[str]) -> str:
    text = f"{subject} {snippet}".lower()
    if "CATEGORY_PROMOTIONS" in labels or any(term in text for term in ("sale", "khuyến mãi", "promotion")):
        return "promotion"
    if "SPAM" in labels:
        return "spam"
    if "CATEGORY_SOCIAL" in labels:
        return "social"
    if any(term in text for term in ("deadline", "hạn nộp", "due", "nộp bài")):
        return "deadline"
    if any(term in text for term in ("meeting", "họp", "seminar")):
        return "meeting"
    if any(term in text for term in ("lớp", "môn", "học", "exam", "thi")):
        return "academic"
    if any(term in text for term in ("nghiên cứu", "paper", "conference", "lab")):
        return "research"
    if any(term in text for term in ("biểu mẫu", "phòng", "quy định", "thông báo")):
        return "admin"
    return "personal"


def priority_hint(subject: str, snippet: str, labels: list[str]) -> str:
    text = f"{subject} {snippet}".lower()
    if "IMPORTANT" in labels or any(term in text for term in ("urgent", "khẩn", "deadline", "hạn nộp")):
        return "high"
    if any(term in text for term in ("meeting", "họp", "thi")):
        return "medium"
    return "low"


def expected_task(subject: str, snippet: str) -> bool:
    text = f"{subject} {snippet}".lower()
    return any(term in text for term in ("deadline", "hạn nộp", "cần", "nộp", "submit", "todo"))

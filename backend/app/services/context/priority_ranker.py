"""Priority scoring for proactive assistant context."""

from __future__ import annotations

from typing import Any

from .entity_extractor import deadline_urgency_score


ACADEMIC_TERMS = {"thi", "lịch thi", "deadline", "hạn nộp", "báo cáo", "seminar", "luận văn", "học bổng"}
ADMIN_TERMS = {"phòng", "biểu mẫu", "quy định", "thông báo", "hành chính"}


def score_email(message: dict[str, Any], deadlines: list[dict[str, Any]]) -> float:
    text = f"{message.get('subject', '')} {message.get('snippet', '')} {message.get('body', '')}".lower()
    score = 0.0
    if message.get("is_unread"):
        score += 0.8
    if message.get("is_important") or message.get("priority_hint") == "high":
        score += 1.4
    if message.get("has_attachment"):
        score += 0.45
    if message.get("expected_task"):
        score += 0.65
    if deadlines:
        score += 1.0 + max(deadline_urgency_score(item.get("date_text")) for item in deadlines)
    if any(term in text for term in ACADEMIC_TERMS):
        score += 0.55
    if any(term in text for term in ADMIN_TERMS):
        score += 0.35
    sender = str(message.get("from") or "").lower()
    if any(term in sender for term in ["edu", "hus", "vnu", "teacher", "lecturer"]):
        score += 0.45
    return round(score, 3)


def score_event(event: dict[str, Any]) -> float:
    score = 0.5
    if event.get("priority_hint") == "high":
        score += 1.2
    if event.get("category") in {"exam", "deadline"}:
        score += 1.1
    if event.get("start_date"):
        score += 0.8
    if event.get("location"):
        score += 0.2
    return round(score, 3)


def score_task(task: dict[str, Any]) -> float:
    score = 0.5
    if task.get("priority") == "high":
        score += 1.4
    if task.get("due_date"):
        score += 0.9 + deadline_urgency_score(str(task.get("due_date")))
    return round(score, 3)

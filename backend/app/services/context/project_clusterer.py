"""Simple heuristic project clustering."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from .context_schema import ContextProject


STOPWORDS = {
    "thong",
    "bao",
    "lich",
    "han",
    "nop",
    "email",
    "gmail",
    "calendar",
    "meeting",
    "class",
    "mon",
    "hoc",
    "cua",
    "cho",
    "google",
    "https",
    "accounts",
    "classroom",
    "notification",
    "forwarded",
    "message",
    "reply",
    "no",
    "thông",
    "báo",
    "lịch",
    "hạn",
    "nộp",
    "môn",
    "học",
    "của",
    "cài",
    "đặt",
}


def cluster_projects(source_items: list[dict[str, Any]]) -> list[ContextProject]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in source_items:
        key = project_key(item)
        if key:
            buckets[key].append(item)

    projects: list[ContextProject] = []
    for key, items in buckets.items():
        if len(items) < 1:
            continue
        keywords = top_keywords(" ".join(str(item.get("title", "")) for item in items))
        projects.append(
            ContextProject(
                project_id=f"project:{slug(key)}",
                name=key.title(),
                keywords=keywords,
                source_ids=[str(item.get("source_id")) for item in items if item.get("source_id")],
                update_count=len(items),
                score=round(len(items) + len(keywords) * 0.1, 3),
            )
        )
    projects.sort(key=lambda item: item.score, reverse=True)
    return projects[:12]


def project_key(item: dict[str, Any]) -> str | None:
    text = f"{item.get('title', '')} {item.get('text', '')}".lower()
    if looks_like_boilerplate(text):
        return None
    explicit = re.findall(r"(?:dự án|du an|project|đồ án|do an|luận văn|luan van)\s+([a-zà-ỹ0-9][^,.;:\n]{2,50})", text, flags=re.IGNORECASE)
    if explicit:
        candidate = cleanup(explicit[0])
        return None if is_bad_project_name(candidate) else candidate
    keywords = top_keywords(text)
    if not keywords:
        return None
    candidate = " ".join(keywords[:2])
    return None if is_bad_project_name(candidate) else candidate


def top_keywords(text: str) -> list[str]:
    words = [
        cleanup(word)
        for word in re.findall(r"[A-Za-zÀ-ỹ0-9]{3,}", text.lower())
        if cleanup(word) and cleanup(word) not in STOPWORDS
    ]
    return [word for word, _count in Counter(words).most_common(5)]


def cleanup(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" -_")).strip()


def looks_like_boilerplate(text: str) -> bool:
    blocked_fragments = (
        "accounts.google",
        "classroom.google",
        "google.com/url",
        "cài đặt thông báo",
        "cai dat thong bao",
        "forwarded message",
    )
    return any(fragment in text for fragment in blocked_fragments)


def is_bad_project_name(value: str) -> bool:
    normalized = cleanup(re.sub(r"[^a-z0-9à-ỹ]+", " ", value.lower()))
    blocked = {
        "google",
        "https",
        "google https",
        "accounts google",
        "classroom google",
        "notification",
        "thong bao",
        "cai dat",
        "lop hoc",
        "lớp học",
        "forwarded message",
        "no reply",
    }
    return normalized in blocked or "https" in normalized or "accounts google" in normalized


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "general"

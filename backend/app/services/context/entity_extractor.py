"""Rule-based entity extraction for personal assistant context."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from email.utils import parseaddr
from typing import Any


ACTION_TERMS = [
    "nộp",
    "gửi",
    "hoàn thành",
    "chuẩn bị",
    "đăng ký",
    "phản hồi",
    "đọc",
    "xem",
    "họp",
    "báo cáo",
    "submit",
    "send",
    "prepare",
    "register",
    "reply",
]

COURSE_PATTERNS = [
    r"môn\s+([A-ZÀ-Ỵa-zà-ỵ0-9][^,.;:\n]{2,80})",
    r"học phần\s+([A-ZÀ-Ỵa-zà-ỵ0-9][^,.;:\n]{2,80})",
    r"course\s+([A-ZÀ-Ỵa-zà-ỵ0-9][^,.;:\n]{2,80})",
]


def extract_email_address(value: str) -> str:
    return parseaddr(value or "")[1].lower()


def extract_people_from_email(message: dict[str, Any]) -> list[dict[str, str]]:
    people = []
    for field in ["from", "to", "cc"]:
        raw = str(message.get(field) or "")
        if not raw:
            continue
        for part in raw.split(","):
            name, email = parseaddr(part)
            if email:
                people.append({"name": name or email.split("@")[0], "email": email.lower(), "role": field})
    return people


def extract_organizations(text: str) -> list[str]:
    organizations = []
    for term in ["HUS", "VNU", "ĐHQGHN", "Đại học Khoa học Tự nhiên", "Khoa học Tự nhiên"]:
        if term.lower() in text.lower():
            organizations.append(term)
    email_domains = re.findall(r"@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
    organizations.extend(sorted(set(email_domains)))
    return sorted(set(organizations))


def extract_courses(text: str) -> list[str]:
    courses: list[str] = []
    for pattern in COURSE_PATTERNS:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            cleaned = re.sub(r"\s+", " ", match).strip(" -")
            if cleaned:
                courses.append(cleaned[:80])
    return sorted(set(courses))


def extract_deadlines(text: str, *, source_id: str, source_type: str) -> list[dict[str, Any]]:
    normalized = re.sub(r"\s+", " ", text or "")
    results: list[dict[str, Any]] = []
    patterns = [
        r"(?:hạn|deadline|due|trước)\s*(?:nộp|gửi|submit)?\s*(?:là|vào|trước)?\s*(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)",
        r"(?:trước|before)\s*(\d{1,2})h",
        r"(?:thứ\s*[A-Za-zÀ-Ỵà-ỵ]+|Friday|Monday|Tuesday|Wednesday|Thursday|Saturday|Sunday)",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, normalized, flags=re.IGNORECASE):
            value = match if isinstance(match, str) else str(match)
            results.append(
                {
                    "deadline_id": f"{source_type}:{source_id}:deadline:{len(results)}",
                    "title": deadline_title(normalized),
                    "date_text": value,
                    "source_type": source_type,
                    "source_id": source_id,
                }
            )
    return results


def deadline_title(text: str) -> str:
    for term in ACTION_TERMS:
        index = text.lower().find(term)
        if index >= 0:
            return text[max(0, index - 40) : index + 140].strip()
    return text[:160].strip() or "Deadline"


def has_action_verb(text: str) -> bool:
    lowered = (text or "").lower()
    return any(term in lowered for term in ACTION_TERMS)


def deadline_urgency_score(date_text: str | None) -> float:
    if not date_text:
        return 0.0
    parsed = parse_vague_date(date_text)
    if not parsed:
        return 0.2
    days = (parsed - date.today()).days
    if days < 0:
        return 0.1
    if days <= 1:
        return 1.0
    if days <= 3:
        return 0.8
    if days <= 7:
        return 0.55
    return 0.25


def parse_vague_date(value: str) -> date | None:
    value = (value or "").strip()
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"]:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    if re.fullmatch(r"\d{1,2}h", value.lower()):
        return date.today()
    weekday_terms = {
        "thứ hai": 0,
        "thứ ba": 1,
        "thứ tư": 2,
        "thứ năm": 3,
        "thứ sáu": 4,
        "thứ bảy": 5,
        "chủ nhật": 6,
        "friday": 4,
        "monday": 0,
    }
    lowered = value.lower()
    for term, weekday in weekday_terms.items():
        if term in lowered:
            today = date.today()
            delta = (weekday - today.weekday()) % 7
            return today + timedelta(days=delta)
    return None

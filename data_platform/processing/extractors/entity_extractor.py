"""Rule-based entity mention extraction for institutional chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from data_platform.processing.cleaners.text_cleaner import normalize_text

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.-]?\d){8,10}(?!\d)")
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4})\b",
    re.I,
)

TITLE_NAME_RE = re.compile(
    r"\b(?:GS\.?TS\.?|PGS\.?TS\.?|TS\.?|ThS\.?|CN\.?)\s+"
    r"([A-ZĐ][\wÀ-ỹ]+(?:\s+[A-ZĐ][\wÀ-ỹ]+){1,5})"
)

DEPARTMENT_PATTERNS = (
    "Khoa Toán - Cơ - Tin học",
    "Khoa Vật lý",
    "Khoa Hóa học",
    "Khoa Sinh học",
    "Khoa Địa chất",
    "Khoa Địa lý",
    "Khoa Môi trường",
    "Khoa Khí tượng Thủy văn và Hải dương học",
)

PROGRAM_PATTERNS = (
    "Khoa học dữ liệu",
    "Khoa học Máy tính và Thông tin",
    "Toán tin",
    "Toán ứng dụng",
    "Công nghệ kỹ thuật hạt nhân",
    "Quản lý tài nguyên và môi trường",
    "Khoa học môi trường",
)


@dataclass(frozen=True)
class EntityMention:
    type: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def extract_entity_mentions(text: str) -> list[dict[str, str]]:
    mentions: list[EntityMention] = []
    normalized = normalize_text(text)

    for email in EMAIL_RE.findall(normalized):
        mentions.append(EntityMention(type="email", text=email))
    for phone in PHONE_RE.findall(normalized):
        mentions.append(EntityMention(type="phone", text=phone))
    for date_value in DATE_RE.findall(normalized):
        mentions.append(EntityMention(type="date", text=date_value))
    for name in TITLE_NAME_RE.findall(normalized):
        mentions.append(EntityMention(type="person", text=name.strip()))

    lowered = normalized.lower()
    for department in DEPARTMENT_PATTERNS:
        if department.lower() in lowered:
            mentions.append(EntityMention(type="department", text=department))
    for program in PROGRAM_PATTERNS:
        if program.lower() in lowered:
            mentions.append(EntityMention(type="program", text=program))

    deduped: dict[tuple[str, str], EntityMention] = {}
    for mention in mentions:
        deduped[(mention.type, mention.text.lower())] = mention
    return [mention.to_dict() for mention in deduped.values()]

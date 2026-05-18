"""Rule-based extraction for explicit memories and tasks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class ExtractedMemory:
    memory_type: str
    content: str
    importance: float


@dataclass(frozen=True)
class ExtractedTask:
    title: str
    due_date: date | None
    priority: str


REMEMBER_PATTERNS = [
    r"(?:hay nho|ghi nho|nho rang|remember that|remember)\s*[:,-]?\s*(.+)",
    r"(?:hãy nhớ|ghi nhớ|nhớ rằng|remember that|remember)\s*[:,-]?\s*(.+)",
    r"(?:tôi muốn bạn nhớ|toi muon ban nho)\s*[:,-]?\s*(.+)",
]

TASK_PATTERNS = [
    r"(?:todo|viec can lam|can lam|phai lam|nhac toi|remind me)\s*[:,-]?\s*(.+)",
    r"(?:todo|việc cần làm|cần làm|phải làm|nhắc tôi|remind me)\s*[:,-]?\s*(.+)",
    r"(.+\b(?:deadline|hạn chót|hạn nộp)\b.+)",
]


class RuleBasedMemoryExtractor:
    def extract_memories(
        self,
        text: str,
        *,
        forced_memory_type: str | None = None,
        forced_importance: float = 0.6,
    ) -> list[ExtractedMemory]:
        cleaned = " ".join(text.split())
        memories: list[ExtractedMemory] = []
        for pattern in REMEMBER_PATTERNS:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                content = match.group(1).strip(" .")
                if content:
                    memories.append(
                        ExtractedMemory(
                            memory_type=forced_memory_type or self.classify_memory(content),
                            content=content,
                            importance=forced_importance,
                        )
                    )
        memories = dedupe_memories(memories)
        if forced_memory_type and not memories:
            memories.append(
                ExtractedMemory(
                    memory_type=forced_memory_type,
                    content=cleaned,
                    importance=forced_importance,
                )
            )
        return memories

    def extract_tasks(self, text: str) -> list[ExtractedTask]:
        cleaned = " ".join(text.split())
        tasks: list[ExtractedTask] = []
        for pattern in TASK_PATTERNS:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                title = match.group(1).strip(" .")
                if title:
                    tasks.append(
                        ExtractedTask(
                            title=title[:300],
                            due_date=extract_due_date(title),
                            priority=classify_priority(title),
                        )
                    )
        return dedupe_tasks(tasks)

    @staticmethod
    def classify_memory(text: str) -> str:
        lowered = text.lower()
        if any(term in lowered for term in ["tôi thích", "toi thich", "ưu tiên", "uu tien", "preference", "prefer"]):
            return "preference"
        if any(term in lowered for term in ["mỗi tuần", "hàng tuần", "hằng ngày", "recurring", "định kỳ"]):
            return "recurring_task"
        if any(term in lowered for term in ["tôi là", "toi la", "lớp", "mã sinh viên", "profile"]):
            return "profile"
        return "fact"


def extract_due_date(text: str) -> date | None:
    lowered = text.lower()
    today = date.today()
    if "hôm nay" in lowered or "hom nay" in lowered:
        return today
    if "ngày mai" in lowered or "ngay mai" in lowered or "tomorrow" in lowered:
        return today + timedelta(days=1)

    iso_match = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
    if iso_match:
        return safe_date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))

    vi_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?\b", text)
    if vi_match:
        year = int(vi_match.group(3)) if vi_match.group(3) else today.year
        return safe_date(year, int(vi_match.group(2)), int(vi_match.group(1)))
    return None


def classify_priority(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ["gấp", "urgent", "asap", "deadline", "hạn chót", "hạn nộp"]):
        return "high"
    if any(term in lowered for term in ["khi rảnh", "low", "không gấp"]):
        return "low"
    return "medium"


def safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def dedupe_tasks(tasks: list[ExtractedTask]) -> list[ExtractedTask]:
    seen: set[str] = set()
    unique: list[ExtractedTask] = []
    for task in tasks:
        key = task.title.lower()
        if key not in seen:
            seen.add(key)
            unique.append(task)
    return unique


def dedupe_memories(memories: list[ExtractedMemory]) -> list[ExtractedMemory]:
    seen: set[tuple[str, str]] = set()
    unique: list[ExtractedMemory] = []
    for memory in memories:
        key = (memory.memory_type, memory.content.lower())
        if key not in seen:
            seen.add(key)
            unique.append(memory)
    return unique

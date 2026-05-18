"""Context-aware assistant planning.

This module keeps routing deterministic, but gives the assistant enough
conversation awareness to behave less like a demo command switchboard.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any


Intent = str


@dataclass(frozen=True)
class AssistantPlan:
    intent: Intent
    confidence: float
    reasons: list[str]
    retrieval_query: str
    top_k: int = 5
    use_llm: bool = True
    contextual_rewrite: bool = False

    def to_metadata(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "retrieval_query": self.retrieval_query,
            "top_k": self.top_k,
            "use_llm": self.use_llm,
            "contextual_rewrite": self.contextual_rewrite,
        }


def build_plan(message: str, *, recent_turns: list[dict[str, Any]] | None = None) -> AssistantPlan:
    text = normalize_text(message)
    recent_turns = recent_turns or []
    previous_institutional_query = find_recent_institutional_query(recent_turns)

    memory_match = contains_any(text, ["hay nho", "ghi nho", "nho rang", "remember"])
    if memory_match:
        return AssistantPlan(
            intent="memory",
            confidence=0.95,
            reasons=["explicit_memory_command"],
            retrieval_query=message,
            use_llm=False,
        )

    if contains_any(text, ["hom nay toi can lam gi", "daily briefing", "can lam gi hom nay", "briefing"]):
        return AssistantPlan(
            intent="daily_briefing",
            confidence=0.92,
            reasons=["daily_briefing_request"],
            retrieval_query=message,
            use_llm=False,
        )

    if contains_any(text, ["lich hom nay", "lich cua toi", "calendar", "su kien hom nay"]):
        return AssistantPlan(
            intent="calendar",
            confidence=0.9,
            reasons=["calendar_request"],
            retrieval_query=message,
            use_llm=False,
        )

    if contains_any(text, ["email", "mail", "gmail", "thu chua doc", "tom tat mail", "tom tat email"]):
        return AssistantPlan(
            intent="gmail",
            confidence=0.9,
            reasons=["gmail_request"],
            retrieval_query=message,
            use_llm=False,
        )

    if contains_any(text, ["task", "todo", "viec can lam", "chua xong", "deadline nao", "nhiem vu"]):
        return AssistantPlan(
            intent="tasks",
            confidence=0.9,
            reasons=["task_memory_request"],
            retrieval_query=message,
            use_llm=False,
        )

    if looks_institutional_query(text):
        return AssistantPlan(
            intent="rag",
            confidence=0.88,
            reasons=["institutional_terms"],
            retrieval_query=message,
            top_k=6,
            use_llm=True,
        )

    if previous_institutional_query and looks_like_followup(text):
        return AssistantPlan(
            intent="rag",
            confidence=0.78,
            reasons=["contextual_institutional_followup"],
            retrieval_query=f"{previous_institutional_query}. Cau hoi tiep theo: {message}",
            top_k=6,
            use_llm=True,
            contextual_rewrite=True,
        )

    if looks_like_general_question(text) and contains_any(text, INSTITUTIONAL_SOFT_TERMS):
        return AssistantPlan(
            intent="rag",
            confidence=0.68,
            reasons=["soft_institutional_question"],
            retrieval_query=message,
            top_k=6,
            use_llm=True,
        )

    return AssistantPlan(
        intent="fallback",
        confidence=0.35,
        reasons=["no_supported_intent_detected"],
        retrieval_query=message,
        use_llm=False,
    )


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    without_marks = without_marks.replace("đ", "d")
    return re.sub(r"\s+", " ", without_marks).strip()


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def find_recent_institutional_query(recent_turns: list[dict[str, Any]]) -> str | None:
    for turn in reversed(recent_turns[-8:]):
        if turn.get("role") != "user":
            continue
        content = str(turn.get("content") or "").strip()
        if looks_institutional_query(normalize_text(content)):
            return content
        metadata = turn.get("metadata") or {}
        if metadata.get("intent") == "rag":
            return content
    return None


def looks_like_followup(text: str) -> bool:
    if not text:
        return False
    word_count = len(text.split())
    followup_markers = [
        "do",
        "nay",
        "ay",
        "nganh do",
        "chuong trinh do",
        "truong do",
        "khoa do",
        "them",
        "cu the",
        "hoc gi",
        "mon nao",
        "bao nhieu",
        "dieu kien",
        "hoc phi",
        "chi tieu",
        "co tot khong",
        "ra truong",
    ]
    return word_count <= 16 and (
        contains_any(text, followup_markers)
        or text.endswith("?")
        or contains_any(text, ["la gi", "nhu the nao", "o dau"])
    )


def looks_like_general_question(text: str) -> bool:
    return bool(text.endswith("?") or contains_any(text, ["la gi", "nhu the nao", "co khong", "bao nhieu"]))


INSTITUTIONAL_SOFT_TERMS = [
    "nganh",
    "mon hoc",
    "tin chi",
    "xet tuyen",
    "diem chuan",
    "dau vao",
    "dau ra",
    "tot nghiep",
    "hoc phan",
    "khoa",
    "truong",
]


def looks_institutional_query(text: str) -> bool:
    terms = [
        "khoa hoc du lieu",
        "chuong trinh dao tao",
        "giang vien",
        "can bo",
        "tuyen sinh",
        "hoc phi",
        "hoc bong",
        "quy che",
        "quy dinh",
        "lich thi",
        "lich hoc",
        "thac si",
        "tien si",
        "khoa hoc may tinh",
        "toan tin",
        "truong dai hoc khoa hoc tu nhien",
        "dai hoc khoa hoc tu nhien",
        "vnu",
        "hus",
    ]
    return contains_any(text, terms)

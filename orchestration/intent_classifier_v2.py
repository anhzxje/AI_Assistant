"""Conversation-aware rule-based intent classifier."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.services.conversation.context_builder import ConversationContext
from orchestration.assistant_brain import normalize_text


@dataclass(frozen=True)
class IntentClassification:
    intent: str
    confidence: float
    reasons: list[str]
    rewritten_query: str | None = None

    def to_metadata(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "rewritten_query": self.rewritten_query,
        }


def classify_intent_v2(message: str, context: ConversationContext | None = None) -> IntentClassification:
    text = normalize_text(message)
    context = context or empty_context()

    if is_empty_message(text):
        return IntentClassification("fallback", 0.99, ["empty_input"])

    if is_unsafe_or_unsupported(text):
        return IntentClassification("fallback", 0.96, ["unsafe_or_unsupported_request"])

    if context.has_followup_reference and is_institutional_query(text):
        rewritten = None
        if context.last_topic_hint:
            rewritten = f"{context.last_topic_hint}. Cau hoi tiep theo: {message}"
        elif "nganh nay" in text and "hoc lap trinh" in text:
            rewritten = "Khoa học dữ liệu có học lập trình không?"
        return IntentClassification(
            "institutional_rag",
            0.88,
            ["institutional_terms_with_followup_words"],
            rewritten_query=rewritten,
        )

    if context.has_followup_reference and not context.last_topic_hint:
        return IntentClassification(
            intent="clarification",
            confidence=0.86,
            reasons=["followup_reference_without_topic"],
        )

    if context.has_followup_reference and context.last_topic_hint:
        previous = context.previous_intent or "general_chat"
        if previous in {"rag"}:
            previous = "institutional_rag"
        if previous in {"fallback", "clarification"}:
            previous = "general_chat"
        return IntentClassification(
            intent=previous,
            confidence=0.82,
            reasons=["followup_reference_with_topic"],
            rewritten_query=f"{context.last_topic_hint}. Cau hoi tiep theo: {message}",
        )

    if contains_any(text, ["hay nho", "ghi nho", "nho rang", "remember"]):
        return IntentClassification("personal_memory", 0.95, ["explicit_memory_command"])

    if contains_any(text, [
        "chuan bi cho cuoc hop",
        "chuan bi hop",
        "chuan bi cho lich thi",
        "chuan bi lich thi",
        "chuan bi cho su kien",
        "chuan bi su kien",
        "tao bao cao",
        "viet bao cao",
        "bao cao hom nay",
        "bao cao tuan nay",
        "viet phan hoi email",
        "viet phan hoi lich su cho email",
        "soan email tra loi",
        "soan email",
        "email draft",
    ]):
        return IntentClassification("action_studio", 0.93, ["action_studio_draft_request"])

    if contains_any(text, [
        "hom nay toi can lam gi",
        "daily briefing",
        "can lam gi hom nay",
        "briefing",
        "chuan bi cho hom nay",
        "co viec gi gap",
        "tom tat cong viec hom nay",
        "toi co deadline nao khong",
        "deadline nao khong",
    ]):
        return IntentClassification("daily_briefing", 0.94, ["daily_briefing_request"])

    if contains_any(text, ["lich hom nay", "lich cua toi", "calendar", "su kien hom nay", "co lich gi", "lich gi", "toi sap hop gi", "sap hop gi"]):
        return IntentClassification("calendar", 0.92, ["calendar_request"])

    if contains_any(text, ["email", "mail", "gmail", "thu chua doc", "tom tat mail", "tom tat email", "email nao quan trong"]) and not is_email_writing_request(text):
        return IntentClassification("gmail", 0.92, ["gmail_request"])

    if contains_any(text, ["tien do du an", "du an"]) and contains_any(text, ["the nao", "sao", "cap nhat", "tien do"]):
        return IntentClassification("daily_briefing", 0.88, ["project_context_request"])

    if contains_any(text, ["task", "todo", "viec can lam", "chua xong", "deadline nao", "nhiem vu"]):
        return IntentClassification("tasks", 0.91, ["task_request"])

    if is_date_time_query(text):
        return IntentClassification("date_time", 0.94, ["date_time_request"])

    if is_institutional_query(text):
        return IntentClassification("institutional_rag", 0.9, ["institutional_terms"])

    if is_general_chat(text) or is_meaningful_general_input(text):
        return IntentClassification("general_chat", 0.78, ["general_chat_terms"])

    return IntentClassification("fallback", 0.35, ["no_supported_intent_detected"])


def empty_context() -> ConversationContext:
    return ConversationContext(
        recent_messages=[],
        conversation_summary="",
        has_followup_reference=False,
        last_topic_hint=None,
        last_sources=[],
        previous_intent=None,
    )


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def is_empty_message(text: str) -> bool:
    return not text or not text.strip()


def is_unsafe_or_unsupported(text: str) -> bool:
    dangerous_terms = [
        "che tao bom",
        "lam bom",
        "vu khi sinh hoc",
        "dau doc",
        "hack tai khoan",
        "danh cap mat khau",
        "ma doc",
    ]
    return contains_any(text, dangerous_terms)


def is_institutional_query(text: str) -> bool:
    hard_terms = [
        "hus",
        "vnu",
        "dhqghn",
        "dai hoc quoc gia ha noi",
        "dai hoc khoa hoc tu nhien",
        "truong dai hoc khoa hoc tu nhien",
        "khtn",
    ]
    leadership_terms = [
        "hieu truong",
        "pho hieu truong",
        "ban giam hieu",
        "lanh dao truong",
        "hoi dong truong",
        "co cau to chuc",
    ]
    institutional_terms = [
        "chuong trinh dao tao",
        "tuyen sinh",
        "hoc phi",
        "hoc bong",
        "diem chuan",
        "xet tuyen",
        "quy che",
        "quy dinh",
        "thong bao",
        "lich thi",
        "lich hoc",
        "giang vien",
        "can bo",
        "phong ban",
        "khoa dao tao",
        "thac si",
        "tien si",
        "nganh hoc",
        "hoc phan",
    ]
    program_context_terms = [
        "hoc nhung mon",
        "hoc gi",
        "hoc mon gi",
        "hoc lap trinh",
        "chuong trinh",
        "dao tao",
        "tuyen sinh",
        "diem chuan",
        "hoc phi",
        "nganh nay",
    ]
    if contains_any(text, hard_terms) or contains_any(text, leadership_terms):
        return True
    if contains_any(text, institutional_terms):
        return True
    if "khoa hoc du lieu" in text and contains_any(text, program_context_terms):
        return True
    return False


def is_date_time_query(text: str) -> bool:
    date_terms = [
        "hom nay la ngay nao",
        "hom nay thu may",
        "bay gio la may gio",
        "bay gio may gio",
        "may gio roi",
        "ngay mai la ngay nao",
        "hom qua la ngay nao",
        "ngay hien tai",
        "thoi gian hien tai",
    ]
    if contains_any(text, date_terms):
        return True
    if contains_any(text, ["hom nay", "ngay mai", "hom qua"]) and contains_any(text, ["ngay nao", "thu may", "ngay may"]):
        return True
    return False


def is_email_writing_request(text: str) -> bool:
    return contains_any(text, ["viet email", "soan email", "viet giup toi email", "email xin", "thu xin"])


def is_general_chat(text: str) -> bool:
    general_terms = [
        "xin chao",
        "chao",
        "hello",
        "hi",
        "ban la ai",
        "gioi thieu ve ban",
        "giai thich",
        "ai la gi",
        "viet giup toi",
        "viet email",
        "xin nghi hoc",
        "tom tat doan nay",
        "tom tat",
        "dich giup",
        "dich cau nay",
        "sang tieng anh",
        "sang tieng viet",
        "sua cau",
        "sua doan van",
        "lap dan y",
        "lap ke hoach",
        "hoc ielts",
        "code",
        "python",
        "doc file csv",
        "goi y",
        "y tuong",
        "ke chuyen",
    ]
    return contains_any(text, general_terms)


def is_meaningful_general_input(text: str) -> bool:
    if len(text) < 2 or looks_like_nonsense(text):
        return False
    common_words = [
        "toi",
        "ban",
        "minh",
        "hay",
        "giup",
        "viet",
        "dich",
        "sua",
        "giai thich",
        "lap",
        "ke hoach",
        "hoc",
        "code",
        "python",
        "email",
        "ai",
        "la gi",
        "nhu the nao",
        "tai sao",
        "cho toi",
        "ve",
        "trong",
    ]
    if contains_any(text, common_words):
        return True
    return looks_like_question(text) and len(text.split()) >= 3


def looks_like_nonsense(text: str) -> bool:
    tokens = text.split()
    if not tokens:
        return True
    known_noise = sum(token in {"asdf", "asdfgh", "qwerty", "zzz", "xxxx"} for token in tokens)
    if known_noise:
        return True
    if len(tokens) >= 2 and not contains_any(
        text,
        ["hello", "hi", "chao", "ai", "toi", "ban", "hoc", "email", "python", "code"],
    ):
        vowel_tokens = sum(any(ch in token for ch in "aeiouy") for token in tokens)
        if vowel_tokens <= len(tokens) // 2:
            return True
    alnum = [ch for ch in text if ch.isalnum()]
    if alnum and sum(ch.isdigit() for ch in alnum) / len(alnum) > 0.7:
        return True
    return False


def looks_like_question(text: str) -> bool:
    return text.endswith("?") or contains_any(text, ["la gi", "nhu the nao", "tai sao", "bao nhieu", "co khong"])

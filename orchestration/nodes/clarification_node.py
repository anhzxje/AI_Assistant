"""Clarification node for underspecified assistant requests."""

from __future__ import annotations

from typing import Any

from orchestration.assistant_brain import normalize_text


def run(state: dict[str, Any]) -> dict[str, Any]:
    text = normalize_text(state.get("message", ""))
    context = state.get("conversation_context") or {}
    last_topic = context.get("last_topic_hint")

    if any(term in text for term in ["thay do", "co do", "giang vien do"]) and not last_topic:
        answer = "Bạn đang nói đến giảng viên nào? Bạn có thể nhập tên thầy/cô hoặc mở lại nguồn liên quan."
    elif context.get("has_followup_reference") and not last_topic:
        answer = "Bạn muốn hỏi tiếp về nội dung nào: chương trình đào tạo, giảng viên, lịch hôm nay, email hay task?"
    elif context.get("has_followup_reference") and last_topic:
        answer = f"Bạn muốn hỏi tiếp về '{last_topic}' theo hướng nào: điều kiện, môn học, học phí, giảng viên hay việc cần làm?"
    else:
        answer = "Bạn có thể nói rõ hơn mục tiêu câu hỏi không: thông tin HUS, lịch, email, task, trí nhớ cá nhân hay trò chuyện tổng quát?"

    state["answer"] = answer
    state["sources"] = []
    state["actions"] = ["clarification_requested"]
    state["memory_used"] = False
    state["metadata"]["general_llm_mode"] = "not_used"
    return state

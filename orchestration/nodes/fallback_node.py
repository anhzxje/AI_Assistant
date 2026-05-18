"""Fallback node."""

from __future__ import annotations


def run(state: dict) -> dict:
    reasons = (state.get("metadata") or {}).get("intent_classifier", {}).get("reasons", [])
    if "unsafe_or_unsupported_request" in reasons:
        answer = "Mình không thể hỗ trợ yêu cầu này. Bạn có thể hỏi mình về học tập, viết lách, lập trình, dịch thuật, HUS, lịch, email, task hoặc ghi nhớ cá nhân."
    elif "empty_input" in reasons:
        answer = "Bạn hãy nhập một câu hỏi hoặc yêu cầu cụ thể để mình hỗ trợ."
    else:
        answer = "Mình chưa hiểu rõ yêu cầu này. Bạn có thể viết lại thành một câu hỏi cụ thể hơn."
    state["answer"] = answer
    state["sources"] = []
    state["actions"] = ["fallback_suggestion"]
    state["memory_used"] = False
    state["metadata"]["general_llm_mode"] = "not_used"
    return state

"""General chat node backed by local Ollama when available."""

from __future__ import annotations

from typing import Any

from backend.app.api.memory import get_memory_context_service
from backend.app.services.llm_service import OllamaService
from data_platform.processing.cleaners.text_cleaner import normalize_for_match


FALLBACK_MESSAGE = (
    "Hiện mình chưa kết nối được mô hình ngôn ngữ tổng quát trên máy. "
    "Mình vẫn có thể hỗ trợ các câu hỏi dựa trên dữ liệu đã nạp, lịch, email mẫu, task và ghi nhớ cá nhân. "
    "Bạn có thể bật Ollama để mình trả lời linh hoạt hơn."
)


def run(state: dict[str, Any]) -> dict[str, Any]:
    llm = OllamaService()
    state["sources"] = []
    state["actions"] = ["general_chat"]
    state["memory_used"] = False

    identity_answer = deterministic_identity_answer(state.get("message", ""))
    if identity_answer:
        state["answer"] = identity_answer
        state["metadata"]["general_llm_mode"] = "not_used"
        return state

    available = llm.is_available()
    if not available:
        llm.warmup()
        available = llm.is_available()
    if not available:
        state["answer"] = FALLBACK_MESSAGE
        state["metadata"]["general_llm_mode"] = "disabled"
        state["metadata"]["llm_error"] = llm.last_error or "ollama_unreachable"
        return state

    prompt = build_general_prompt(state)
    generated = llm.generate(prompt, temperature=0.2)
    if not generated:
        generated = llm.chat(
            [
                {"role": "system", "content": "Bạn là Lumi, trợ lý tiếng Việt ngắn gọn, tự nhiên, không bịa thông tin."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            num_ctx=2048,
        )
    if not generated:
        state["answer"] = FALLBACK_MESSAGE
        state["metadata"]["general_llm_mode"] = "disabled"
        state["metadata"]["llm_error"] = llm.last_error or "ollama_generation_failed"
        return state

    state["answer"] = generated
    state["metadata"]["general_llm_mode"] = "ollama"
    state["metadata"]["llm_error"] = None
    state["memory_used"] = bool(state.get("metadata", {}).get("memory_items"))
    return state


def build_general_prompt(state: dict[str, Any]) -> str:
    context = state.get("conversation_context") or {}
    recent = context.get("recent_messages") or []
    recent_lines = []
    for item in recent[-8:]:
        role = item.get("role")
        content = " ".join(str(item.get("content") or "").split())
        if role and content:
            recent_lines.append(f"{role}: {content[:500]}")

    memory_block = "No personal memory context."
    if state.get("include_memory", True):
        try:
            memory_context = get_memory_context_service().build_context(
                user_id=state["user_id"],
                query=state["message"],
                session_id=state.get("session_id"),
                limit=5,
            )
            if memory_context.item_count:
                memory_block = memory_context.to_prompt_block()
                state["metadata"]["memory_items"] = memory_context.item_count
        except Exception:
            state["metadata"]["memory_warning"] = "memory context unavailable"

    role = state.get("auth_role") or state.get("role") or "user"
    role_hint = (
        "The user is an admin; include data, QA, and governance framing when useful."
        if role == "admin"
        else "The user is a normal user; keep the framing personal and practical."
    )

    return f"""You are OmniAssistant, a local-first assistant for the OmniAssistant project.

Answer in Vietnamese unless the user asks otherwise.
For general questions, be helpful but do not invent institutional facts.
Do not claim that HUS, VNU, or another institution created you.
If the user asks about HUS policy, admissions, programs, faculty, schedules, email, tasks, or memory, say that those should use the specialized tools.
{role_hint}

CONVERSATION:
{chr(10).join(recent_lines) if recent_lines else "No recent conversation."}

MEMORY:
{memory_block}

USER:
{state["message"]}

ANSWER:
"""


def deterministic_identity_answer(message: str) -> str | None:
    normalized = normalize_for_match(message)
    if normalized in {"ban la ai", "ban la gi", "omni la ai"} or "ban la ai" in normalized:
        return (
            "Tôi là OmniAssistant, trợ lý AI chạy cục bộ cho dự án này. "
            "Tôi có thể trò chuyện tổng quát khi Ollama đang bật, và có các tuyến chuyên biệt cho hỏi đáp HUS, "
            "trí nhớ cá nhân, task, lịch, email mẫu và briefing."
        )
    return None

"""Gmail summary node."""

from __future__ import annotations

from backend.app.api.google import get_personal_ingestion_service
from backend.app.services.context.context_engine import ContextEngine
from backend.app.services.llm_service import OllamaService


def run(state: dict) -> dict:
    service = get_personal_ingestion_service()
    stats = service.sync_gmail(
        user_id=state["user_id"],
        max_results=100 if not state.get("use_mock_google", False) else 20,
        use_mock=state.get("use_mock_google", False),
        query="newer_than:90d",
    )
    if not stats.connected:
        state["answer"] = "Gmail chưa được kết nối. Bạn có thể kết nối Gmail trong Cài đặt hoặc bật dữ liệu mẫu để demo."
        state["sources"] = [{"type": "gmail", "source_mode": "not_connected"}]
        state["actions"] = ["gmail_not_connected"]
        state["metadata"]["google"] = {
            "source_mode": "not_connected",
            "gmail_connected": False,
            "message_count": 0,
            "unread_count": 0,
            "read_count": 0,
            "important_count": 0,
        }
        state["memory_used"] = False
        return state
    summary = service.gmail_summary(user_id=state["user_id"])
    context = ContextEngine().build(user_id=state["user_id"])
    important = context.important_emails[:5]
    messages = important or summary.get("recent_messages", [])[:5]
    lines = [
        f"Email summary: {summary['total_messages']} total, {summary['unread_count']} unread, {summary['important_count']} important."
    ]
    for message in messages:
        label = "important" if message in important else "recent"
        lines.append(f"- [{label}] {message.get('subject') or '(No subject)'}: {message.get('snippet', '')[:160]}")
    fallback = "\n".join(lines)
    state["answer"] = synthesize_email_summary(fallback) or fallback
    state["sources"] = [{"type": "gmail", "message_id": item.get("message_id"), "subject": item.get("subject")} for item in messages]
    state["actions"] = ["gmail_readonly_sync", "gmail_mock_sync" if state.get("use_mock_google", False) else "gmail_real_sync"]
    state["metadata"]["google"] = {
        "source_mode": summary.get("source_mode"),
        "gmail_connected": summary.get("source_mode") == "real",
        "message_count": summary.get("total_messages", 0),
        "unread_count": summary.get("unread_count", 0),
        "read_count": summary.get("read_count", 0),
        "important_count": summary.get("important_count", 0),
        "context_priorities": len(context.priorities),
    }
    state["memory_used"] = False
    return state


def synthesize_email_summary(fallback: str) -> str | None:
    llm = OllamaService()
    if not llm.is_available():
        return None
    return llm.generate(
        f"""Rewrite this read-only email summary in Vietnamese. Keep all counts and do not invent messages.

EMAIL_SUMMARY:
{fallback}

ANSWER:
""",
        temperature=0.2,
    )

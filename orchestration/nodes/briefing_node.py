"""Smart daily briefing node."""

from __future__ import annotations

from backend.app.api.google import get_personal_ingestion_service
from backend.app.services.briefing.smart_briefing import SmartBriefingService


def run(state: dict) -> dict:
    service = get_personal_ingestion_service()
    gmail_stats = service.sync_gmail(
        user_id=state["user_id"],
        max_results=100 if not state.get("use_mock_google", False) else 20,
        use_mock=state.get("use_mock_google", False),
        query="newer_than:90d",
    )
    calendar_stats = service.sync_calendar(
        user_id=state["user_id"],
        days_ahead=30,
        include_all_calendars=True,
        include_holidays=False,
        use_mock=state.get("use_mock_google", False),
    )
    if not calendar_stats.connected:
        service.clear_calendar_for_user(user_id=state["user_id"])
    if not gmail_stats.connected:
        service.clear_gmail_for_user(user_id=state["user_id"])

    briefing = SmartBriefingService().generate(user_id=state["user_id"])
    answer_lines = [f"Daily briefing: {briefing.morning_report}"]
    if briefing.top_priorities:
        answer_lines.append("\nƯu tiên:")
        for priority in briefing.top_priorities[:5]:
            answer_lines.append(f"- {priority.get('title')} ({priority.get('reason')})")
    if briefing.suggested_actions:
        answer_lines.append("\nGợi ý hành động:")
        for action in briefing.suggested_actions[:4]:
            answer_lines.append(f"- {action.get('title')}")

    state["answer"] = "\n".join(answer_lines).strip()
    state["metadata"]["general_llm_mode"] = "ollama" if briefing.metadata.get("llm_used") else "not_used"
    state["sources"] = briefing.sources or [
        {"type": "smart_briefing", "generated_at": briefing.generated_at},
        {"type": "gmail", "records_synced": gmail_stats.records_synced, "source_mode": gmail_stats.source_mode},
        {"type": "calendar", "records_synced": calendar_stats.records_synced, "source_mode": calendar_stats.source_mode},
    ]
    state["actions"] = ["smart_daily_briefing", "context_engine_build"]
    gmail_source = "mock" if gmail_stats.source_mode == "mock" else ("real" if gmail_stats.connected else "none")
    calendar_source = "mock" if calendar_stats.source_mode == "mock" else ("real" if calendar_stats.connected else "none")
    source_mode = briefing.metadata.get("source_mode")
    if "real" in {gmail_source, calendar_source} and "none" in {gmail_source, calendar_source}:
        source_mode = "mixed"
    state["metadata"]["smart_briefing"] = briefing.model_dump(mode="json")
    state["metadata"]["google"] = {
        "source_mode": source_mode,
        "gmail_connected": gmail_stats.connected and gmail_stats.source_mode == "real",
        "calendar_connected": calendar_stats.connected and calendar_stats.source_mode == "real",
        "gmail_source": gmail_source,
        "calendar_source": calendar_source,
    }
    state["memory_used"] = bool(briefing.top_priorities or briefing.suggested_actions)
    return state

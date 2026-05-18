"""Generate source-grounded proactive daily briefings."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.config import get_backend_settings
from backend.app.services.connectors.personal_ingestion import write_json
from backend.app.services.context.context_engine import ContextEngine
from backend.app.services.context.context_schema import PersonalContext
from backend.app.services.llm_service import OllamaService

from .briefing_schema import SmartBriefing


class SmartBriefingService:
    def __init__(self) -> None:
        self.data_root = get_backend_settings().data_settings.resolved_data_root
        self.context_engine = ContextEngine()

    def generate(self, *, user_id: str, time_window: str = "today") -> SmartBriefing:
        context = self.context_engine.build(user_id=user_id, time_window=time_window)
        briefing = self._from_context(context)
        self.save(briefing)
        return briefing

    def latest(self, *, user_id: str) -> SmartBriefing:
        path = self._briefing_dir(user_id) / "latest_briefing.json"
        if path.exists():
            return SmartBriefing.model_validate_json(path.read_text(encoding="utf-8"))
        return self.generate(user_id=user_id)

    def save(self, briefing: SmartBriefing) -> None:
        folder = self._briefing_dir(briefing.user_id)
        folder.mkdir(parents=True, exist_ok=True)
        payload = briefing.model_dump(mode="json")
        write_json(folder / "latest_briefing.json", payload)
        write_json(folder / f"briefing_{date.today().isoformat()}.json", payload)

    def _from_context(self, context: PersonalContext) -> SmartBriefing:
        generated_at = datetime.now(timezone.utc).isoformat()
        priorities = [priority.model_dump(mode="json") for priority in context.priorities[:5]]
        events = sorted(context.meetings, key=lambda item: str(item.get("start") or item.get("start_time") or ""))[:8]
        emails = context.important_emails[:8]
        projects = [project.model_dump(mode="json") for project in context.projects[:6]]
        sources = source_items_for(context, priorities, events, emails)

        if not priorities and not events and not emails:
            report = "Hôm nay chưa có email hoặc lịch nào được đồng bộ."
            headline = "Chưa có dữ liệu mới"
        else:
            headline = build_headline(priorities, events, emails)
            fallback = build_morning_report(
                priorities=priorities,
                events=events,
                emails=emails,
                ignored_noise_count=int(context.noise_summary.get("ignored_count") or 0),
            )
            report = synthesize_report(fallback, context) or fallback

        briefing = SmartBriefing(
            briefing_id=f"briefing:{context.user_id}:{date.today().isoformat()}",
            user_id=context.user_id,
            generated_at=generated_at,
            headline=headline,
            morning_report=report,
            top_priorities=priorities,
            upcoming_events=events,
            important_emails=emails,
            suggested_actions=suggested_actions(priorities),
            project_updates=projects,
            ignored_noise_count=int(context.noise_summary.get("ignored_count") or 0),
            sources=sources,
            metadata={
                "llm_used": report != fallback if priorities or events or emails else False,
                "source_mode": source_mode(context),
                "grounded": True,
                "context_generated_at": context.generated_at,
                "message_count": context.metadata.get("message_count", 0),
                "event_count": context.metadata.get("event_count", 0),
            },
        )
        return briefing

    def _briefing_dir(self, user_id: str) -> Path:
        return self.data_root / "features" / "personal" / "briefings" / user_id


def build_headline(priorities: list[dict[str, Any]], events: list[dict[str, Any]], emails: list[dict[str, Any]]) -> str:
    if priorities:
        return str(priorities[0].get("title") or "Có việc cần ưu tiên hôm nay")
    if events:
        return f"Hôm nay có {len(events)} sự kiện cần chú ý"
    return f"Có {len(emails)} email quan trọng cần xem"


def build_morning_report(
    *,
    priorities: list[dict[str, Any]],
    events: list[dict[str, Any]],
    emails: list[dict[str, Any]],
    ignored_noise_count: int,
) -> str:
    parts = ["Chào buổi sáng."]
    if events:
        next_event = events[0]
        time_text = next_event.get("start_time") or "hôm nay"
        parts.append(f"Hôm nay bạn có {len(events)} sự kiện; gần nhất là {next_event.get('summary')} lúc {time_text}.")
    if emails:
        parts.append(f"Có {len(emails)} email cần chú ý.")
    if priorities:
        top = priorities[0]
        parts.append(f"Việc nên ưu tiên là: {top.get('title')}.")
    if ignored_noise_count:
        parts.append(f"Mình đã bỏ qua {ignored_noise_count} email quảng cáo/không liên quan.")
    return " ".join(parts)


def synthesize_report(fallback: str, context: PersonalContext) -> str | None:
    llm = OllamaService()
    if not llm.is_available():
        return None
    source_lines = []
    for priority in context.priorities[:5]:
        source_lines.append(f"- {priority.title} | reason={priority.reason} | source={priority.source_type}:{priority.source_id}")
    prompt = f"""Viết lại briefing sau bằng tiếng Việt tự nhiên, ngắn gọn, có tính chủ động.
Chỉ dùng các mục nguồn bên dưới. Không bịa thêm sự kiện, email, deadline hoặc task.
Nếu dữ liệu ít, nói rõ là dữ liệu còn ít.

BRIEFING NHÁP:
{fallback}

NGUỒN ƯU TIÊN:
{chr(10).join(source_lines)}

TRẢ LỜI:
"""
    generated = llm.generate(prompt, temperature=0.15, num_ctx=2048)
    if not generated:
        return None
    leaked_markers = ["NGUỒN ƯU TIÊN", "BRIEFING NHÁP", "TRẢ LỜI:", "RAW_BRIEFING"]
    if any(marker.lower() in generated.lower() for marker in leaked_markers):
        return None
    return generated


def suggested_actions(priorities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": item.get("suggested_action") or "Xem lại mục ưu tiên.",
            "source_type": item.get("source_type"),
            "source_id": item.get("source_id"),
            "priority_score": item.get("score"),
        }
        for item in priorities[:6]
    ]


def source_items_for(
    context: PersonalContext,
    priorities: list[dict[str, Any]],
    events: list[dict[str, Any]],
    emails: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    wanted = {(item.get("source_type"), item.get("source_id")) for item in priorities}
    wanted.update({("calendar", item.get("event_id")) for item in events})
    wanted.update({("gmail", item.get("message_id")) for item in emails})
    sources = []
    for item in context.source_items:
        if (item.source_type, item.source_id) in wanted:
            sources.append(item.model_dump(mode="json"))
    return sources[:20]


def source_mode(context: PersonalContext) -> str:
    modes = {str(item.metadata.get("source_mode") or item.metadata.get("mode") or "") for item in context.source_items}
    source_modes = {str(item.metadata.get("source_mode") or "") for item in context.source_items}
    modes.update(source_modes)
    if any("real" in mode for mode in modes):
        return "real"
    if any("mock" in mode for mode in modes):
        return "mock"
    if context.metadata.get("message_count") or context.metadata.get("event_count"):
        return "real"
    return "not_connected"

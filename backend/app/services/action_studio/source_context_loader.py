"""Load compact grounded sources for Action Studio drafts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.app.config import get_backend_settings
from backend.app.services.briefing.smart_briefing import SmartBriefingService
from backend.app.services.connectors.personal_ingestion import read_jsonl
from backend.app.services.context.context_engine import ContextEngine
from backend.app.services.knowledge.knowledge_store import KnowledgeStore
from backend.app.services.memory.task_memory import TaskMemoryStore

from .action_schema import SourceBundle, SourceReference


class SourceContextLoader:
    def __init__(self) -> None:
        self.data_root = get_backend_settings().data_settings.resolved_data_root
        self.context_engine = ContextEngine()
        self.briefing_service = SmartBriefingService()
        self.knowledge_store = KnowledgeStore()
        self.task_store = TaskMemoryStore()

    def load(
        self,
        *,
        user_id: str,
        email_id: str | None = None,
        thread_id: str | None = None,
        event_id: str | None = None,
        project_id: str | None = None,
    ) -> SourceBundle:
        context = self.context_engine.latest(user_id=user_id) or self.context_engine.build(user_id=user_id)
        briefing = self.briefing_service.latest(user_id=user_id)
        knowledge = self.knowledge_store.summary(user_id=user_id)
        gmail_messages = self._gmail_messages(user_id)
        calendar_events = self._calendar_events(user_id)
        tasks = [task.model_dump(mode="json") for task in self.task_store.list_tasks(user_id=user_id, status="open", limit=50)]

        selected = {
            "email": find_email(gmail_messages, email_id=email_id, thread_id=thread_id),
            "event": find_event(calendar_events, event_id=event_id),
            "project": find_project(context.model_dump(mode="json").get("projects", []), project_id=project_id),
        }
        source_refs = build_source_refs(
            context=context.model_dump(mode="json"),
            briefing=briefing.model_dump(mode="json"),
            knowledge=knowledge,
            gmail_messages=gmail_messages,
            calendar_events=calendar_events,
            tasks=tasks,
            selected=selected,
        )
        return SourceBundle(
            user_id=user_id,
            context=context.model_dump(mode="json"),
            briefing=briefing.model_dump(mode="json"),
            knowledge_summary=knowledge,
            selected={key: value for key, value in selected.items() if value},
            gmail_messages=gmail_messages[:80],
            calendar_events=calendar_events[:80],
            tasks=tasks[:50],
            sources=source_refs,
            metadata={
                "context_generated_at": context.generated_at,
                "briefing_generated_at": briefing.generated_at,
                "message_count": len(gmail_messages),
                "event_count": len(calendar_events),
                "task_count": len(tasks),
            },
        )

    def _gmail_messages(self, user_id: str) -> list[dict[str, Any]]:
        items = [
            item
            for item in read_jsonl(self.data_root / "processed" / "personal" / "gmail_messages.jsonl")
            if item.get("user_id") == user_id
        ]
        return sorted(items, key=lambda item: str(item.get("date") or ""), reverse=True)

    def _calendar_events(self, user_id: str) -> list[dict[str, Any]]:
        items = [
            item
            for item in read_jsonl(self.data_root / "processed" / "personal" / "calendar_events.jsonl")
            if item.get("user_id") == user_id
        ]
        return sorted(items, key=lambda item: (str(item.get("start_date") or ""), str(item.get("start_time") or "")))


def find_email(messages: list[dict[str, Any]], *, email_id: str | None, thread_id: str | None) -> dict[str, Any] | None:
    for message in messages:
        if email_id and str(message.get("message_id")) == email_id:
            return message
        if thread_id and str(message.get("thread_id")) == thread_id:
            return message
    return None


def find_event(events: list[dict[str, Any]], *, event_id: str | None) -> dict[str, Any] | None:
    if not event_id:
        return None
    for event in events:
        if str(event.get("event_id")) == event_id or str(event.get("raw_event_id")) == event_id:
            return event
    return None


def find_project(projects: list[dict[str, Any]], *, project_id: str | None) -> dict[str, Any] | None:
    if not project_id:
        return None
    for project in projects:
        if str(project.get("project_id")) == project_id:
            return project
    return None


def upcoming_events(events: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    today = date.today()
    upcoming = []
    for event in events:
        try:
            event_date = date.fromisoformat(str(event.get("start_date") or ""))
        except ValueError:
            continue
        if event_date >= today:
            upcoming.append(event)
    return upcoming[:limit]


def build_source_refs(
    *,
    context: dict[str, Any],
    briefing: dict[str, Any],
    knowledge: dict[str, Any],
    gmail_messages: list[dict[str, Any]],
    calendar_events: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    selected: dict[str, Any],
) -> list[SourceReference]:
    refs: list[SourceReference] = []
    for item in selected.values():
        if isinstance(item, dict):
            refs.append(ref_from_record(item, preferred_type="selected"))
    for item in context.get("source_items", [])[:16]:
        refs.append(
            SourceReference(
                source_type=str(item.get("source_type") or "context"),
                source_id=str(item.get("source_id") or ""),
                title=str(item.get("title") or "Context source"),
                text=str(item.get("text") or "")[:700],
                url=item.get("url"),
                metadata=item.get("metadata") or {},
            )
        )
    for event in upcoming_events(calendar_events, limit=8):
        refs.append(ref_from_record(event, preferred_type="calendar"))
    for message in gmail_messages[:8]:
        refs.append(ref_from_record(message, preferred_type="gmail"))
    for task in tasks[:8]:
        refs.append(ref_from_record(task, preferred_type="task"))
    refs.append(
        SourceReference(
            source_type="briefing",
            source_id=str(briefing.get("briefing_id") or "latest"),
            title=str(briefing.get("headline") or "Latest briefing"),
            text=str(briefing.get("morning_report") or "")[:700],
            metadata={"generated_at": briefing.get("generated_at"), "source_mode": briefing.get("metadata", {}).get("source_mode")},
        )
    )
    refs.append(
        SourceReference(
            source_type="knowledge",
            source_id="summary",
            title="Knowledge summary",
            text=f"Nodes: {knowledge.get('node_count', 0)}, edges: {knowledge.get('edge_count', 0)}",
            metadata={
                "node_counts": knowledge.get("node_counts", {}),
                "edge_counts": knowledge.get("edge_counts", {}),
            },
        )
    )
    return dedupe_refs(refs)[:40]


def ref_from_record(record: dict[str, Any], *, preferred_type: str) -> SourceReference:
    if preferred_type == "calendar" or record.get("event_id"):
        return SourceReference(
            source_type="calendar",
            source_id=str(record.get("event_id") or record.get("raw_event_id") or ""),
            title=str(record.get("summary") or "Calendar event"),
            text=str(record.get("description") or ""),
            url=record.get("html_link"),
            metadata={
                "start_date": record.get("start_date"),
                "start_time": record.get("start_time"),
                "calendar_name": record.get("calendar_name"),
                "location": record.get("location"),
                "source_mode": record.get("source_mode"),
            },
        )
    if preferred_type == "gmail" or record.get("message_id"):
        return SourceReference(
            source_type="gmail",
            source_id=str(record.get("message_id") or ""),
            title=str(record.get("subject") or "(No subject)"),
            text=f"{record.get('snippet') or ''}\n{str(record.get('body') or '')[:500]}".strip(),
            metadata={
                "from": record.get("from"),
                "date": record.get("date"),
                "thread_id": record.get("thread_id"),
                "is_unread": record.get("is_unread"),
                "source_mode": record.get("source_mode"),
            },
        )
    return SourceReference(
        source_type="task",
        source_id=str(record.get("task_id") or record.get("source_id") or ""),
        title=str(record.get("title") or "Task"),
        text=str(record.get("source_text") or ""),
        metadata={"due_date": record.get("due_date"), "priority": record.get("priority"), "status": record.get("status")},
    )


def dedupe_refs(refs: list[SourceReference]) -> list[SourceReference]:
    seen: set[tuple[str, str, str]] = set()
    kept: list[SourceReference] = []
    for ref in refs:
        key = (ref.source_type, str(ref.source_id or ""), ref.title)
        if key in seen:
            continue
        seen.add(key)
        kept.append(ref)
    return kept


def format_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d")
    except ValueError:
        return value


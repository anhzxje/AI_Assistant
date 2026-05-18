"""Build structured personal context from synced sources."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.config import get_backend_settings
from backend.app.services.connectors.personal_ingestion import (
    NOISE_CATEGORIES,
    latest_institutional_reminders,
    read_jsonl,
    write_json,
)
from backend.app.services.memory.task_memory import TaskMemoryStore

from .context_schema import ContextPriority, ContextSourceItem, ContextTask, PersonalContext
from .entity_extractor import (
    extract_courses,
    extract_deadlines,
    extract_organizations,
    extract_people_from_email,
    has_action_verb,
)
from .priority_ranker import score_email, score_event, score_task
from .project_clusterer import cluster_projects


class ContextEngine:
    def __init__(self) -> None:
        self.data_root = get_backend_settings().data_settings.resolved_data_root
        self.task_store = TaskMemoryStore()

    def build(self, *, user_id: str, time_window: str = "today") -> PersonalContext:
        generated_at = datetime.now(timezone.utc).isoformat()
        messages = self._gmail_messages(user_id)
        events = self._calendar_events(user_id)
        email_tasks = self._email_tasks(user_id)
        memory_tasks = [task.model_dump(mode="json") for task in self.task_store.list_tasks(user_id=user_id, status="open", limit=50)]

        people_counter: Counter[str] = Counter()
        people_metadata: dict[str, dict[str, Any]] = {}
        organizations: set[str] = set()
        courses: set[str] = set()
        source_items: list[ContextSourceItem] = []
        important_emails: list[dict[str, Any]] = []
        deadlines: list[dict[str, Any]] = []
        meetings: list[dict[str, Any]] = []
        priorities: list[ContextPriority] = []

        for message in messages:
            message_id = str(message.get("message_id") or "")
            text = f"{message.get('subject', '')} {message.get('snippet', '')} {message.get('body', '')}"
            for person in extract_people_from_email(message):
                key = person.get("email") or person.get("name")
                if key:
                    people_counter[key] += 1
                    people_metadata[key] = person
            organizations.update(extract_organizations(text))
            courses.update(extract_courses(text))
            item_deadlines = extract_deadlines(text, source_id=message_id, source_type="gmail")
            deadlines.extend(item_deadlines)
            email_score = score_email(message, item_deadlines)
            source_items.append(
                ContextSourceItem(
                    source_type="gmail",
                    source_id=message_id,
                    title=message.get("subject") or "(No subject)",
                    text=text[:1200],
                    metadata={
                        "from": message.get("from"),
                        "is_unread": message.get("is_unread"),
                        "is_important": message.get("is_important"),
                        "category": message.get("category"),
                        "source_mode": message.get("source_mode"),
                        "score": email_score,
                    },
                )
            )
            if message.get("category") not in NOISE_CATEGORIES and email_score >= 1.0:
                email_item = {**message, "context_score": email_score}
                important_emails.append(email_item)
                priorities.append(
                    ContextPriority(
                        priority_id=f"email:{message_id}",
                        title=message.get("subject") or "Email cần chú ý",
                        reason=priority_reason_for_email(message, item_deadlines),
                        score=email_score,
                        source_type="gmail",
                        source_id=message_id,
                        suggested_action=suggest_action(text, default="Xem email và phản hồi nếu cần."),
                    )
                )

        for event in events:
            event_id = str(event.get("event_id") or "")
            text = f"{event.get('summary', '')} {event.get('description', '')}"
            calendar_suffix = f" ({event.get('calendar_name')})" if event.get("calendar_name") else ""
            if event.get("category") in {"meeting", "seminar", "exam", "deadline", "class"}:
                meetings.append({**event, "context_score": score_event(event)})
            source_items.append(
                ContextSourceItem(
                    source_type="calendar",
                    source_id=event_id,
                    title=f"{event.get('summary') or 'Calendar event'}{calendar_suffix}",
                    text=text[:1000],
                    url=event.get("html_link") or None,
                    metadata={
                        "start": event.get("start"),
                        "start_date": event.get("start_date"),
                        "end": event.get("end"),
                        "calendar_id": event.get("calendar_id"),
                        "calendar_name": event.get("calendar_name"),
                        "is_all_day": event.get("is_all_day"),
                        "category": event.get("category"),
                        "status": event.get("status"),
                        "source_mode": event.get("source_mode"),
                        "score": score_event(event),
                    },
                )
            )
            if event.get("category") != "holiday" and (event.get("start_date") == date.today().isoformat() or event.get("priority_hint") == "high"):
                priorities.append(
                    ContextPriority(
                        priority_id=f"event:{event_id}",
                        title=event.get("summary") or "Sự kiện lịch",
                        reason="Sự kiện trong lịch cần chuẩn bị.",
                        score=score_event(event),
                        source_type="calendar",
                        source_id=event_id,
                        suggested_action="Kiểm tra thời gian, địa điểm và tài liệu cần chuẩn bị.",
                    )
                )

        context_tasks: list[ContextTask] = []
        for raw_task in [*email_tasks, *memory_tasks]:
            source_id = str(raw_task.get("source_id") or raw_task.get("task_id") or raw_task.get("title") or "task")
            scored = score_task(raw_task)
            context_tasks.append(
                ContextTask(
                    task_id=str(raw_task.get("task_id") or f"task:{source_id}"),
                    title=str(raw_task.get("title") or "Task"),
                    due_date=raw_task.get("due_date"),
                    priority=str(raw_task.get("priority") or "medium"),
                    source_type=str(raw_task.get("source") or "task"),
                    source_id=source_id,
                    score=scored,
                )
            )
            priorities.append(
                ContextPriority(
                    priority_id=f"task:{source_id}",
                    title=str(raw_task.get("title") or "Task"),
                    reason="Task đang mở trong bộ nhớ cá nhân.",
                    score=scored,
                    source_type=str(raw_task.get("source") or "task"),
                    source_id=source_id,
                    suggested_action="Hoàn thành hoặc cập nhật trạng thái task.",
                )
            )

        source_dicts = [item.model_dump(mode="json") for item in source_items]
        projects = cluster_projects(source_dicts)
        important_emails.sort(key=lambda item: item.get("context_score", 0), reverse=True)
        priorities.sort(key=lambda item: item.score, reverse=True)

        context = PersonalContext(
            user_id=user_id,
            generated_at=generated_at,
            time_window=time_window,
            people=[
                {**people_metadata[key], "mention_count": count}
                for key, count in people_counter.most_common(20)
            ],
            projects=projects,
            tasks=context_tasks,
            deadlines=deadlines,
            meetings=meetings,
            important_emails=important_emails[:12],
            noise_summary={
                "ignored_count": len([item for item in messages if item.get("category") in NOISE_CATEGORIES]),
                "by_category": dict(Counter(str(item.get("category") or "unknown") for item in messages if item.get("category") in NOISE_CATEGORIES)),
            },
            priorities=priorities[:12],
            knowledge_gaps=knowledge_gaps(messages, events),
            source_items=trim_source_items(source_items, limit=120),
            metadata={
                "message_count": len(messages),
                "event_count": len(events),
                "email_task_count": len(email_tasks),
                "memory_task_count": len(memory_tasks),
                "organizations": sorted(organizations),
                "courses": sorted(courses),
                "institutional_reminders": latest_institutional_reminders(self.data_root),
            },
        )
        self.save(context)
        return context

    def latest(self, *, user_id: str) -> PersonalContext | None:
        path = self._context_dir(user_id) / "latest_context.json"
        if not path.exists():
            return None
        return PersonalContext.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, context: PersonalContext) -> None:
        folder = self._context_dir(context.user_id)
        folder.mkdir(parents=True, exist_ok=True)
        payload = context.model_dump(mode="json")
        write_json(folder / "latest_context.json", payload)
        write_json(folder / f"context_{date.today().isoformat()}.json", payload)

    def _gmail_messages(self, user_id: str) -> list[dict[str, Any]]:
        return [item for item in read_jsonl(self.data_root / "processed" / "personal" / "gmail_messages.jsonl") if item.get("user_id") == user_id]

    def _calendar_events(self, user_id: str) -> list[dict[str, Any]]:
        return [item for item in read_jsonl(self.data_root / "processed" / "personal" / "calendar_events.jsonl") if item.get("user_id") == user_id]

    def _email_tasks(self, user_id: str) -> list[dict[str, Any]]:
        return [item for item in read_jsonl(self.data_root / "features" / "personal" / "tasks_from_email.jsonl") if item.get("user_id") == user_id]

    def _context_dir(self, user_id: str) -> Path:
        return self.data_root / "features" / "personal" / "context" / user_id


def priority_reason_for_email(message: dict[str, Any], deadlines: list[dict[str, Any]]) -> str:
    if deadlines:
        return "Email có hạn chót hoặc mốc thời gian cần xử lý."
    if message.get("is_unread") and message.get("is_important"):
        return "Email chưa đọc và được đánh dấu quan trọng."
    if message.get("has_attachment"):
        return "Email có tệp đính kèm hoặc biểu mẫu cần kiểm tra."
    return "Email liên quan đến học tập/công việc."


def suggest_action(text: str, *, default: str) -> str:
    lowered = (text or "").lower()
    if "nộp" in lowered or "submit" in lowered:
        return "Chuẩn bị và nộp nội dung trước hạn."
    if "phản hồi" in lowered or "reply" in lowered:
        return "Phản hồi email sau khi đọc nội dung."
    if "đăng ký" in lowered or "register" in lowered:
        return "Kiểm tra yêu cầu và hoàn tất đăng ký."
    if has_action_verb(lowered):
        return "Xử lý yêu cầu được nêu trong email."
    return default


def knowledge_gaps(messages: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps = []
    if not messages:
        gaps.append({"type": "gmail", "message": "Chưa có email được đồng bộ."})
    if not events:
        gaps.append({"type": "calendar", "message": "Chưa có sự kiện lịch được đồng bộ."})
    return gaps


def trim_source_items(items: list[ContextSourceItem], *, limit: int) -> list[ContextSourceItem]:
    if len(items) <= limit:
        return items
    calendar_items = [item for item in items if item.source_type == "calendar"]
    other_items = [item for item in items if item.source_type != "calendar"]
    return [*calendar_items, *other_items[: max(0, limit - len(calendar_items))]]

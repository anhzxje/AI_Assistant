"""Personal Gmail/Calendar ingestion and daily briefing feature builder."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from backend.app.config import get_backend_settings
from backend.app.schemas.memory_schema import TaskRecord
from backend.app.services.connectors.calendar_connector import CalendarConnector
from backend.app.services.connectors.gmail_connector import GmailConnector, header_value
from backend.app.services.memory.memory_extractor import ExtractedTask, RuleBasedMemoryExtractor
from backend.app.services.memory.task_memory import TaskMemoryStore


NOISE_CATEGORIES = {"spam", "promotion", "social"}


@dataclass(frozen=True)
class PersonalSyncStats:
    user_id: str
    mode: str
    raw_path: str
    processed_path: str
    features_path: str | None
    records_synced: int
    connected: bool = True
    message: str | None = None
    source_mode: str = "mock"
    metadata: dict[str, Any] | None = None
    calendar_connected: bool | None = None
    calendar_count: int | None = None
    calendars: list[dict[str, Any]] | None = None
    events_count: int | None = None
    today_count: int | None = None
    date_range: dict[str, str] | None = None
    events: list[dict[str, Any]] | None = None


class PersonalIngestionService:
    def __init__(self) -> None:
        self.settings = get_backend_settings().data_settings
        self.gmail = GmailConnector()
        self.calendar = CalendarConnector()
        self.extractor = RuleBasedMemoryExtractor()
        self.task_store = TaskMemoryStore()

    def sync_gmail(
        self,
        *,
        user_id: str,
        max_results: int = 100,
        use_mock: bool = False,
        scenario: str | None = None,
        query: str = "newer_than:90d",
        include_spam_trash: bool = False,
    ) -> PersonalSyncStats:
        started_at = datetime.now(timezone.utc)
        result = self.gmail.fetch_messages(
            user_id=user_id,
            max_results=max_results,
            use_mock=use_mock,
            scenario=scenario,
            query=query,
            include_spam_trash=include_spam_trash,
        )
        if result.mode == "not_connected":
            finished_at = datetime.now(timezone.utc)
            return PersonalSyncStats(
                user_id=user_id,
                mode=result.mode,
                raw_path="",
                processed_path="",
                features_path=None,
                records_synced=0,
                connected=False,
                message="Gmail chưa được kết nối. Bạn có thể dùng dữ liệu mẫu hoặc kết nối Gmail ở trang Cài đặt.",
                source_mode="not_connected",
                metadata=sync_progress_metadata(
                    source_mode="not_connected",
                    started_at=started_at,
                    finished_at=finished_at,
                    requested_max=max_results,
                    fetched_count=0,
                    processed_count=0,
                    query=query,
                ),
            )
        today = date.today().isoformat()
        raw_path = self._data_path("raw", "gmail", today, f"{user_id}_gmail_messages.json")
        processed = [normalize_gmail_message(message, user_id=user_id, mode=result.mode) for message in result.messages]
        counts = gmail_counts(processed)
        finished_at = datetime.now(timezone.utc)
        sync_metadata = {
            "source_mode": "mock" if result.mode.startswith("mock") else "real",
            "total_messages": len(processed),
            **counts,
            "query": query if not use_mock else None,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        sync_metadata.update(
            sync_progress_metadata(
                source_mode=str(sync_metadata["source_mode"]),
                started_at=started_at,
                finished_at=finished_at,
                requested_max=max_results,
                fetched_count=len(result.messages),
                processed_count=len(processed),
                query=query if not use_mock else None,
            )
        )
        write_json(raw_path, {"user_id": user_id, "mode": result.mode, "metadata": sync_metadata, "messages": result.messages})

        processed_path = self._data_path("processed", "personal", filename="gmail_messages.jsonl")
        replace_jsonl_for_user(processed_path, processed, user_id=user_id)

        task_records = []
        for message in processed:
            text = f"{message['subject']} {message['snippet']} {message.get('body', '')}"
            extracted = self.extractor.extract_tasks(text)
            if message.get("expected_task") and not extracted:
                extracted = [
                    ExtractedTask(
                        title=message["subject"][:300],
                        due_date=None,
                        priority=message.get("priority_hint") or "medium",
                    )
                ]
            for task in extracted:
                task_records.append(
                    {
                        "user_id": user_id,
                        "source": "gmail",
                        "source_id": message["message_id"],
                        "title": task.title,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "priority": task.priority,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
        features_path = self._data_path("features", "personal", filename="tasks_from_email.jsonl")
        replace_jsonl_for_user(features_path, task_records, user_id=user_id)
        write_sync_status(self._data_path("features", "personal", filename="google_sync_status.jsonl"), user_id, "gmail", sync_metadata)
        return PersonalSyncStats(
            user_id=user_id,
            mode=result.mode,
            raw_path=str(raw_path),
            processed_path=str(processed_path),
            features_path=str(features_path),
            records_synced=len(processed),
            source_mode="mock" if result.mode.startswith("mock") else "real",
            metadata=sync_metadata,
        )

    def sync_calendar(
        self,
        *,
        user_id: str,
        days_ahead: int = 7,
        start_date: str | None = None,
        end_date: str | None = None,
        calendar_ids: list[str] | None = None,
        include_all_calendars: bool = False,
        include_holidays: bool = False,
        use_mock: bool = False,
        scenario: str | None = None,
        include_cancelled: bool = False,
    ) -> PersonalSyncStats:
        started_at = datetime.now(timezone.utc)
        result = self.calendar.fetch_events(
            user_id=user_id,
            days_ahead=days_ahead,
            start_date=start_date,
            end_date=end_date,
            calendar_ids=calendar_ids,
            include_all_calendars=include_all_calendars,
            include_holidays=include_holidays,
            use_mock=use_mock,
            scenario=scenario,
            include_cancelled=include_cancelled,
        )
        if result.mode == "not_connected":
            finished_at = datetime.now(timezone.utc)
            return PersonalSyncStats(
                user_id=user_id,
                mode=result.mode,
                raw_path="",
                processed_path="",
                features_path=None,
                records_synced=0,
                connected=False,
                message="Calendar chưa được kết nối. Bạn có thể dùng dữ liệu mẫu hoặc kết nối Calendar ở trang Cài đặt.",
                source_mode="not_connected",
                metadata=sync_progress_metadata(
                    source_mode="not_connected",
                    started_at=started_at,
                    finished_at=finished_at,
                    requested_max=days_ahead,
                    fetched_count=0,
                    processed_count=0,
                    days_ahead=days_ahead,
                ),
            )
        events = align_mock_calendar_events(result.events) if use_mock else result.events
        today = date.today().isoformat()
        raw_path = self._data_path("raw", "calendar", today, f"{user_id}_calendar_events.json")
        finished_at = datetime.now(timezone.utc)
        start_dt = parse_iso_date(start_date) if start_date else date.today()
        end_dt = parse_iso_date(end_date) if end_date else start_dt + timedelta(days=max(0, days_ahead))
        if end_dt is None:
            end_dt = start_dt + timedelta(days=max(0, days_ahead))
        calendars = result.calendars or ([default_mock_calendar()] if use_mock else [])
        available_calendars = result.available_calendars or calendars
        sync_metadata = {
            "source_mode": "mock" if result.mode.startswith("mock") else "real",
            "events_count": len(events),
            "calendar_count": len(calendars),
            "calendars": calendars,
            "available_calendars": available_calendars,
            "days_ahead": days_ahead,
            "date_range": result.date_range or {"start_date": start_dt.isoformat(), "end_date": end_dt.isoformat()},
            "calendar_ids": calendar_ids or [calendar.get("id") for calendar in calendars],
            "include_all_calendars": include_all_calendars,
            "include_holidays": include_holidays,
            "include_cancelled": include_cancelled,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        sync_metadata.update(
            sync_progress_metadata(
                source_mode=str(sync_metadata["source_mode"]),
                started_at=started_at,
                finished_at=finished_at,
                requested_max=days_ahead,
                fetched_count=len(events),
                processed_count=0,
                days_ahead=days_ahead,
                start_date=start_dt.isoformat(),
                end_date=end_dt.isoformat(),
            )
        )
        write_json(raw_path, {"user_id": user_id, "mode": result.mode, "metadata": sync_metadata, "calendars": calendars, "events": events})

        processed = [
            normalize_calendar_event(event, user_id=user_id, mode=result.mode)
            for event in events
            if event_in_range(event, start_date=start_dt, end_date=end_dt)
        ]
        processed_path = self._data_path("processed", "personal", filename="calendar_events.jsonl")
        replace_jsonl_for_user(processed_path, processed, user_id=user_id)
        sync_metadata["today_count"] = len(
            [event for event in processed if parse_iso_date(event.get("start_date")) == date.today()]
        )
        sync_metadata["processed_count"] = len(processed)
        write_sync_status(self._data_path("features", "personal", filename="google_sync_status.jsonl"), user_id, "calendar", sync_metadata)
        return PersonalSyncStats(
            user_id=user_id,
            mode=result.mode,
            raw_path=str(raw_path),
            processed_path=str(processed_path),
            features_path=None,
            records_synced=len(processed),
            source_mode="mock" if result.mode.startswith("mock") else "real",
            metadata=sync_metadata,
            calendar_connected=True,
            calendar_count=len(calendars),
            calendars=calendars,
            events_count=len(processed),
            today_count=sync_metadata["today_count"],
            date_range=sync_metadata["date_range"],
            events=processed,
        )

    def list_calendars(self, *, user_id: str) -> list[dict[str, Any]]:
        return self.calendar.list_calendars(user_id=user_id)

    def clear_calendar_for_user(self, *, user_id: str) -> None:
        replace_jsonl_for_user(self._data_path("processed", "personal", filename="calendar_events.jsonl"), [], user_id=user_id)
        write_sync_status(
            self._data_path("features", "personal", filename="google_sync_status.jsonl"),
            user_id,
            "calendar",
            {
                "source_mode": "not_connected",
                "events_count": 0,
                "today_count": 0,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def clear_gmail_for_user(self, *, user_id: str) -> None:
        replace_jsonl_for_user(self._data_path("processed", "personal", filename="gmail_messages.jsonl"), [], user_id=user_id)
        replace_jsonl_for_user(self._data_path("features", "personal", filename="tasks_from_email.jsonl"), [], user_id=user_id)
        write_sync_status(
            self._data_path("features", "personal", filename="google_sync_status.jsonl"),
            user_id,
            "gmail",
            {
                "source_mode": "not_connected",
                "total_messages": 0,
                "unread_count": 0,
                "read_count": 0,
                "important_count": 0,
                "noise_count": 0,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def gmail_summary(self, *, user_id: str) -> dict[str, Any]:
        messages = [
            item
            for item in read_jsonl(self._data_path("processed", "personal", filename="gmail_messages.jsonl"))
            if item.get("user_id") == user_id
        ]
        unread = [item for item in messages if item.get("is_unread")]
        important = [item for item in messages if item.get("is_important")]
        read_count = len(messages) - len(unread)
        return {
            "user_id": user_id,
            "total": len(messages),
            "total_messages": len(messages),
            "unread": len(unread),
            "unread_count": len(unread),
            "read": read_count,
            "read_count": read_count,
            "important": len(important),
            "important_count": len(important),
            "noise_ignored": len([item for item in messages if item.get("category") in NOISE_CATEGORIES]),
            "noise_count": len([item for item in messages if item.get("category") in NOISE_CATEGORIES]),
            "top_senders": dict(Counter(item.get("from", "") for item in messages).most_common(5)),
            "recent_messages": messages[-10:][::-1],
            "source_mode": infer_source_mode(messages),
        }

    def today_calendar(self, *, user_id: str) -> dict[str, Any]:
        today = date.today()
        events = [
            item
            for item in read_jsonl(self._data_path("processed", "personal", filename="calendar_events.jsonl"))
            if item.get("user_id") == user_id and parse_iso_date(item.get("start_date")) == today
        ]
        events.sort(key=lambda item: item.get("start_time") or "")
        sync_status = read_sync_status(self.settings.resolved_data_root, user_id, "calendar") or {}
        source_mode = infer_source_mode(events)
        if not events and sync_status.get("source_mode") in {"real", "mock", "not_connected"}:
            source_mode = str(sync_status["source_mode"])
        return {"user_id": user_id, "date": today.isoformat(), "events": events, "source_mode": source_mode}

    def daily_briefing(self, *, user_id: str) -> dict[str, Any]:
        email_summary = self.gmail_summary(user_id=user_id)
        today_calendar = self.today_calendar(user_id=user_id)
        email_tasks = [
            item
            for item in read_jsonl(self._data_path("features", "personal", filename="tasks_from_email.jsonl"))
            if item.get("user_id") == user_id
        ]
        memory_tasks = [task.model_dump(mode="json") for task in self.task_store.list_tasks(user_id=user_id, status="open", limit=10)]
        messages = [
            item
            for item in read_jsonl(self._data_path("processed", "personal", filename="gmail_messages.jsonl"))
            if item.get("user_id") == user_id
        ]
        important_emails = select_important_emails(messages)
        ignored_noise_count = len([item for item in messages if item.get("category") in NOISE_CATEGORIES])
        tasks = [*email_tasks[-10:], *memory_tasks]
        priorities = build_priorities(today_calendar["events"], email_summary, email_tasks, memory_tasks)
        briefing = {
            "user_id": user_id,
            "date": date.today().isoformat(),
            "summary": build_briefing_summary(
                events=today_calendar["events"],
                important_emails=important_emails,
                tasks=tasks,
                ignored_noise_count=ignored_noise_count,
            ),
            "important_emails": important_emails,
            "ignored_noise_count": ignored_noise_count,
            "today_events": today_calendar["events"],
            "email_summary": email_summary,
            "extracted_email_tasks": email_tasks[-10:],
            "tasks": tasks,
            "task_memory": memory_tasks,
            "priorities": priorities,
            "institutional_reminders": latest_institutional_reminders(self.settings.resolved_data_root),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "source_mode": combine_source_modes(
                    str(email_summary.get("source_mode") or "not_connected"),
                    str(today_calendar.get("source_mode") or "not_connected"),
                ),
                "gmail_connected": email_summary.get("source_mode") == "real",
                "calendar_connected": today_calendar.get("source_mode") == "real",
            },
        }
        output_path = self._data_path("features", "personal", filename="daily_briefing.json")
        write_json(output_path, briefing)
        return briefing

    def sync_status(self, *, user_id: str, integration: str) -> dict[str, Any]:
        status = read_sync_status(self.settings.resolved_data_root, user_id, integration) or {}
        if not status:
            return {
                "user_id": user_id,
                "integration": integration,
                "status": "idle",
                "source_mode": "not_connected",
                "fetched_count": 0,
                "processed_count": 0,
            }
        return {"status": "completed", **status}

    def _data_path(self, layer: str, domain: str, *parts: str, filename: str | None = None) -> Path:
        path = self.settings.resolved_data_root / layer / domain
        for part in parts:
            path = path / part
        if filename:
            path = path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def normalize_gmail_message(message: dict[str, Any], *, user_id: str, mode: str) -> dict[str, Any]:
    labels = set(message.get("labelIds") or message.get("labels") or [])
    date_header = header_value(message, "Date")
    parsed_date = parse_email_date(date_header)
    return {
        "message_id": message.get("id"),
        "thread_id": message.get("threadId") or message.get("thread_id"),
        "user_id": user_id,
        "from": header_value(message, "From"),
        "to": header_value(message, "To"),
        "cc": message.get("cc") or header_value(message, "Cc"),
        "subject": header_value(message, "Subject"),
        "internal_date": message.get("internalDate"),
        "date": parsed_date.isoformat() if parsed_date else None,
        "snippet": message.get("snippet") or "",
        "body": message.get("body_text") or message.get("body") or "",
        "category": message.get("category") or "unknown",
        "priority_hint": message.get("priority_hint") or "medium",
        "expected_task": bool(message.get("expected_task")),
        "has_attachment": bool(message.get("has_attachment")),
        "attachments": message.get("attachments") or [],
        "is_unread": bool(message.get("is_unread")) or "UNREAD" in labels,
        "is_important": bool(message.get("is_important")) or "IMPORTANT" in labels,
        "is_starred": bool(message.get("is_starred")) or "STARRED" in labels,
        "labels": sorted(str(label) for label in labels),
        "source_mode": mode,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


def normalize_calendar_event(event: dict[str, Any], *, user_id: str, mode: str) -> dict[str, Any]:
    start = coerce_event_time(event.get("start"))
    end = coerce_event_time(event.get("end"))
    start_value = start.get("dateTime") or start.get("date")
    end_value = end.get("dateTime") or end.get("date")
    start_dt = parse_datetime_or_date(start_value)
    end_dt = parse_datetime_or_date(end_value)
    calendar_id = event.get("calendar_id") or "primary"
    raw_event_id = event.get("id")
    return {
        "event_id": f"{calendar_id}:{raw_event_id}" if raw_event_id and calendar_id else raw_event_id,
        "raw_event_id": raw_event_id,
        "user_id": user_id,
        "calendar_id": calendar_id,
        "calendar_name": event.get("calendar_name") or "Primary",
        "summary": event.get("summary") or "",
        "description": event.get("description") or "",
        "location": event.get("location") or "",
        "html_link": event.get("htmlLink") or event.get("html_link") or "",
        "start": start_value,
        "end": end_value,
        "is_all_day": bool(event.get("is_all_day")) or bool(start.get("date") and not start.get("dateTime")),
        "start_date": start_dt.date().isoformat() if start_dt else None,
        "start_time": start_dt.time().isoformat(timespec="minutes") if start_dt and "T" in str(start_value) else None,
        "end_date": end_dt.date().isoformat() if end_dt else None,
        "attendees": event.get("attendees") or [],
        "status": event.get("status") or "unknown",
        "category": event.get("category") or "unknown",
        "priority_hint": event.get("priority_hint") or "medium",
        "date_range": event.get("date_range") or {},
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "source_mode": mode,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


def default_mock_calendar() -> dict[str, Any]:
    return {
        "id": "mock-primary",
        "summary": "Mock Calendar",
        "primary": True,
        "selected": True,
        "accessRole": "owner",
        "is_holiday": False,
        "is_classroom": False,
    }


def align_mock_calendar_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not events:
        return []
    base_date = first_event_date(events)
    if base_date is None:
        return events
    delta = date.today() - base_date
    if delta.days == 0:
        return events

    aligned = []
    for event in events:
        item = dict(event)
        for key in ["start", "end"]:
            value = coerce_event_time(item.get(key))
            if value.get("dateTime"):
                shifted = parse_datetime_or_date(value["dateTime"])
                if shifted:
                    value["dateTime"] = (shifted + delta).isoformat()
            elif value.get("date"):
                shifted_date = parse_iso_date(value["date"])
                if shifted_date:
                    value["date"] = (shifted_date + delta).isoformat()
            item[key] = value
        aligned.append(item)
    return aligned


def first_event_date(events: list[dict[str, Any]]) -> date | None:
    for event in events:
        start_obj = coerce_event_time(event.get("start"))
        start = start_obj.get("dateTime") or start_obj.get("date")
        parsed = parse_datetime_or_date(start)
        if parsed:
            return parsed.date()
    return None


def event_in_range(event: dict[str, Any], *, start_date: date, end_date: date) -> bool:
    start_obj = coerce_event_time(event.get("start"))
    start = start_obj.get("dateTime") or start_obj.get("date")
    parsed = parse_datetime_or_date(start)
    if not parsed:
        return False
    return start_date <= parsed.date() <= end_date


def build_priorities(
    events: list[dict[str, Any]],
    email_summary: dict[str, Any],
    email_tasks: list[dict[str, Any]],
    memory_tasks: list[dict[str, Any]],
) -> list[str]:
    priorities: list[str] = []
    if events:
        priorities.append(f"Attend {len(events)} calendar event(s) today.")
    if email_summary.get("unread_count"):
        priorities.append(f"Review {email_summary['unread_count']} unread email(s).")
    urgent_tasks = [task for task in [*email_tasks, *memory_tasks] if task.get("priority") == "high"]
    if urgent_tasks:
        priorities.append(f"Handle {len(urgent_tasks)} high-priority task(s).")
    if not priorities:
        priorities.append("No urgent personal items found in synced mock data.")
    return priorities


def select_important_emails(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    useful = [
        item
        for item in messages
        if item.get("category") not in NOISE_CATEGORIES
        and (item.get("is_important") or item.get("priority_hint") == "high" or item.get("expected_task"))
    ]
    useful.sort(key=lambda item: (item.get("priority_hint") != "high", item.get("date") or ""), reverse=False)
    return useful[:8]


def build_briefing_summary(
    *,
    events: list[dict[str, Any]],
    important_emails: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    ignored_noise_count: int,
) -> str:
    if not events and not important_emails and not tasks:
        return "Hôm nay chưa có email hoặc lịch nào được đồng bộ."
    parts: list[str] = []
    if events:
        parts.append(f"Hôm nay có {len(events)} sự kiện trong lịch.")
    if important_emails:
        parts.append(f"Có {len(important_emails)} email quan trọng cần chú ý.")
    if tasks:
        high = len([task for task in tasks if task.get("priority") == "high"])
        parts.append(f"Có {len(tasks)} tác vụ được trích xuất" + (f", trong đó {high} việc ưu tiên cao." if high else "."))
    if ignored_noise_count:
        parts.append("Mình đã bỏ qua các email quảng cáo/không liên quan.")
    return " ".join(parts)


def latest_institutional_reminders(data_root: Path) -> list[dict[str, str]]:
    docs_root = data_root / "processed" / "documents"
    if not docs_root.exists():
        return []
    files = sorted(docs_root.glob("*/processed_documents.jsonl"), reverse=True)
    if not files:
        return []
    reminders = []
    for item in read_jsonl(files[0]):
        if item.get("document_type") == "announcement":
            reminders.append({"title": item.get("title") or "Untitled", "source_url": item.get("source_url") or ""})
        if len(reminders) >= 3:
            break
    return reminders


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def upsert_jsonl_by_id(path: Path, records: list[dict[str, Any]], *, key: str) -> None:
    existing = {str(item.get(key)): item for item in read_jsonl(path) if item.get(key) is not None}
    for record in records:
        if record.get(key) is not None:
            existing[str(record[key])] = record
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in existing.values():
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def replace_jsonl_for_user(path: Path, records: list[dict[str, Any]], *, user_id: str) -> None:
    existing = [item for item in read_jsonl(path) if item.get("user_id") != user_id]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in [*existing, *records]:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def write_sync_status(path: Path, user_id: str, integration: str, metadata: dict[str, Any]) -> None:
    record = {
        "sync_key": f"{user_id}:{integration}",
        "user_id": user_id,
        "integration": integration,
        **metadata,
    }
    upsert_jsonl_by_id(path, [record], key="sync_key")


def sync_progress_metadata(
    *,
    source_mode: str,
    started_at: datetime,
    finished_at: datetime,
    requested_max: int,
    fetched_count: int,
    processed_count: int,
    **extra: Any,
) -> dict[str, Any]:
    elapsed_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
    return {
        "status": "completed" if source_mode != "not_connected" else "not_connected",
        "requested_max": requested_max,
        "fetched_count": fetched_count,
        "processed_count": processed_count,
        "total_estimated": fetched_count,
        "elapsed_ms": elapsed_ms,
        "estimated_remaining_ms": 0,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        **extra,
    }


def read_sync_status(data_root: Path, user_id: str, integration: str) -> dict[str, Any] | None:
    path = data_root / "features" / "personal" / "google_sync_status.jsonl"
    key = f"{user_id}:{integration}"
    for item in read_jsonl(path):
        if item.get("sync_key") == key:
            return item
    return None


def gmail_counts(messages: list[dict[str, Any]]) -> dict[str, int]:
    unread = len([item for item in messages if item.get("is_unread")])
    important = len([item for item in messages if item.get("is_important")])
    noise = len([item for item in messages if item.get("category") in NOISE_CATEGORIES])
    return {
        "unread_count": unread,
        "read_count": len(messages) - unread,
        "important_count": important,
        "noise_count": noise,
    }


def infer_source_mode(items: list[dict[str, Any]]) -> str:
    if not items:
        return "not_connected"
    modes = {str(item.get("source_mode") or "") for item in items}
    if any(mode == "real" for mode in modes):
        return "real"
    if any(mode.startswith("mock") for mode in modes):
        return "mock"
    return "not_connected"


def combine_source_modes(gmail_mode: str, calendar_mode: str) -> str:
    modes = {gmail_mode, calendar_mode}
    if "real" in modes and "mock" in modes:
        return "mixed"
    if "real" in modes:
        return "real"
    if "mock" in modes:
        return "mock"
    return "not_connected"


def parse_email_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(value)
    except Exception:
        return None


def coerce_event_time(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {"dateTime": value} if "T" in value else {"date": value}
    return {}


def parse_datetime_or_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if "T" in value:
            return datetime.fromisoformat(value)
        return datetime.fromisoformat(f"{value}T00:00:00")
    except ValueError:
        return None


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None

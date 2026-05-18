from __future__ import annotations

import json
from pathlib import Path

from backend.app.services.context.context_engine import ContextEngine


class EmptyTaskStore:
    def list_tasks(self, **kwargs):
        return []


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records), encoding="utf-8")


def test_context_engine_extracts_deadline_and_ranks_urgent_email(tmp_path: Path) -> None:
    user_id = "context-test"
    write_jsonl(
        tmp_path / "processed" / "personal" / "gmail_messages.jsonl",
        [
            {
                "message_id": "m1",
                "user_id": user_id,
                "from": "Giảng viên <teacher@hus.edu.vn>",
                "to": "student@example.com",
                "subject": "Thông báo lịch thi môn Khai phá dữ liệu",
                "snippet": "Hạn nộp báo cáo trước 17h thứ Sáu",
                "body": "Bạn cần nộp báo cáo trước 17h thứ Sáu.",
                "category": "deadline",
                "priority_hint": "high",
                "expected_task": True,
                "is_unread": True,
                "is_important": True,
                "source_mode": "real",
            },
            {
                "message_id": "m2",
                "user_id": user_id,
                "from": "ads@example.com",
                "subject": "Sale cuối tuần",
                "snippet": "Khuyến mãi",
                "category": "promotion",
                "is_unread": False,
                "is_important": False,
                "source_mode": "real",
            },
        ],
    )
    write_jsonl(tmp_path / "processed" / "personal" / "calendar_events.jsonl", [])
    write_jsonl(tmp_path / "features" / "personal" / "tasks_from_email.jsonl", [])

    engine = ContextEngine()
    engine.data_root = tmp_path
    engine.task_store = EmptyTaskStore()
    context = engine.build(user_id=user_id)

    assert context.deadlines
    assert context.priorities[0].source_id == "m1"
    assert context.noise_summary["ignored_count"] == 1
    assert context.people[0]["email"] == "teacher@hus.edu.vn"


def test_context_engine_extracts_meeting_from_calendar(tmp_path: Path) -> None:
    user_id = "calendar-context-test"
    write_jsonl(tmp_path / "processed" / "personal" / "gmail_messages.jsonl", [])
    write_jsonl(
        tmp_path / "processed" / "personal" / "calendar_events.jsonl",
        [
            {
                "event_id": "e1",
                "user_id": user_id,
                "summary": "Họp seminar lab",
                "description": "Chuẩn bị báo cáo tiến độ",
                "start_date": __import__("datetime").date.today().isoformat(),
                "start_time": "14:00",
                "category": "meeting",
                "priority_hint": "medium",
                "source_mode": "real",
            }
        ],
    )
    write_jsonl(tmp_path / "features" / "personal" / "tasks_from_email.jsonl", [])

    engine = ContextEngine()
    engine.data_root = tmp_path
    engine.task_store = EmptyTaskStore()
    context = engine.build(user_id=user_id)

    assert context.meetings
    assert context.priorities[0].source_type == "calendar"

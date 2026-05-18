from __future__ import annotations

from backend.app.services.action_studio.context_sanitizer import sanitize_email, sanitize_event, sanitize_task
from backend.app.services.action_studio.meeting_prep import (
    exam_prep_content,
    meeting_prep_content,
    no_meeting_content,
    select_event,
)


def test_meeting_prep_does_not_select_exam_as_meeting() -> None:
    event = exam_event()
    assert select_event([event], query_profile="chuan bi cho cuoc hop hom nay", query_kind="meeting") is None


def test_exam_event_uses_exam_prep_format() -> None:
    event = sanitize_event(exam_event())
    content = exam_prep_content(event, query="chuẩn bị cho lịch thi Khai phá dữ liệu")
    assert "## Chuẩn bị cho lịch thi" in content
    assert "## Chuẩn bị cuộc họp" not in content
    assert "23001857@hus.edu.vn" not in content


def test_user_facing_output_contains_no_calendar_id_or_noisy_text() -> None:
    event = sanitize_event(exam_event())
    email = sanitize_email(
        {
            "subject": "Forwarded message Cài đặt thông báo <https://accounts.google.com>",
            "from": "Dung Vu Tien (Lớp học) <no-reply@classroom.google.com>",
            "snippet": "Cài đặt thông báo <https://accounts.google.com> Forwarded message",
            "body": "Forwarded message https://classroom.google.com",
        }
    )
    task = sanitize_task({"title": "Cài đặt thông báo <https://accounts.google.com> Forwarded message cần nộp báo cáo rất dài" * 5})

    content = meeting_prep_content(event=event, project={"name": "Google Https"}, emails=[email], tasks=[task], people=[], query="chuẩn bị họp")

    assert "23001857@hus.edu.vn" not in content
    assert "Forwarded message" not in content
    assert "Cài đặt thông báo" not in content
    assert "https://accounts.google" not in content
    assert len(task["title"]) <= 163


def test_meeting_prep_limits_people_emails_tasks() -> None:
    event = sanitize_event({"summary": "Họp nhóm", "start_date": "2026-05-16", "start_time": "09:00"})
    people = [{"name": f"Person {index}"} for index in range(10)]
    emails = [{"subject": f"Email {index}", "sender": f"Sender {index}"} for index in range(10)]
    tasks = [{"title": f"Task {index}"} for index in range(10)]

    content = meeting_prep_content(event=event, project=None, emails=emails, tasks=tasks, people=people, query="chuẩn bị họp")

    assert "Person 5" not in content
    assert "Task 5" not in content


def test_no_meeting_asks_clarification() -> None:
    content = no_meeting_content([exam_event()])
    assert "chưa thấy cuộc họp" in content
    assert "Bạn muốn mình chuẩn bị cho sự kiện nào" in content


def test_llm_polished_output_guardrails_are_represented() -> None:
    event = sanitize_event({"summary": "Họp nhóm nghiên cứu", "start_date": "2026-05-16", "start_time": "09:00"})
    content = meeting_prep_content(event=event, project=None, emails=[], tasks=[], people=[], query="chuẩn bị họp")

    assert "## Chuẩn bị cuộc họp" in content
    assert "Google Https" not in content
    assert "Forwarded message" not in content
    assert "Cài đặt thông báo" not in content


def exam_event() -> dict:
    return {
        "event_id": "calendar-event-1",
        "summary": "Lịch thi Khai phá dữ liệu [23001857@hus.edu.vn]",
        "calendar_name": "23001857@hus.edu.vn",
        "category": "exam",
        "start_date": "2026-05-16",
        "start_time": "08:00:00",
        "location": "Phòng 201",
    }

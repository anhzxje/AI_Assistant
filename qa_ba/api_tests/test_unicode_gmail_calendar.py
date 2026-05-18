"""Unicode regression tests for personal Gmail/Calendar ingestion."""

from __future__ import annotations

import uuid

from backend.app.services.connectors.gmail_connector import GmailSyncResult
from backend.app.services.connectors.personal_ingestion import PersonalIngestionService, read_jsonl


def test_vietnamese_gmail_text_preserved_in_json_outputs(monkeypatch) -> None:
    user_id = f"unicode-{uuid.uuid4()}"
    subject = "Thông báo lịch thi môn Khai phá dữ liệu"
    body = "Hạn nộp báo cáo trước 17h thứ Sáu"

    def fake_fetch_messages(**kwargs):
        return GmailSyncResult(
            user_id=kwargs["user_id"],
            mode="real",
            messages=[
                {
                    "id": "unicode-message",
                    "thread_id": "thread-1",
                    "from": "teacher@example.com",
                    "to": "student@example.com",
                    "subject": subject,
                    "snippet": body,
                    "body": body,
                    "date": "2026-05-16T09:00:00+07:00",
                    "labels": ["INBOX", "UNREAD", "IMPORTANT"],
                    "category": "deadline",
                    "priority_hint": "high",
                    "expected_task": True,
                }
            ],
        )

    service = PersonalIngestionService()
    monkeypatch.setattr(service.gmail, "fetch_messages", fake_fetch_messages)

    stats = service.sync_gmail(user_id=user_id, use_mock=False)
    records = [item for item in read_jsonl(service._data_path("processed", "personal", filename="gmail_messages.jsonl")) if item.get("user_id") == user_id]

    assert stats.source_mode == "real"
    assert records[0]["subject"] == subject
    assert records[0]["body"] == body
    assert "?" not in records[0]["subject"]
    assert "?" not in records[0]["body"]

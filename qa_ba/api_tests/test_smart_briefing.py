from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.briefing.smart_briefing import SmartBriefingService
from backend.app.services.context.context_engine import ContextEngine
from qa_ba.api_tests.auth_helpers import user_headers


class EmptyTaskStore:
    def list_tasks(self, **kwargs):
        return []


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records), encoding="utf-8")


def service_for(tmp_path: Path) -> SmartBriefingService:
    engine = ContextEngine()
    engine.data_root = tmp_path
    engine.task_store = EmptyTaskStore()
    service = SmartBriefingService()
    service.data_root = tmp_path
    service.context_engine = engine
    return service


def test_smart_briefing_empty_does_not_hallucinate(tmp_path: Path) -> None:
    user_id = "empty-smart"
    write_jsonl(tmp_path / "processed" / "personal" / "gmail_messages.jsonl", [])
    write_jsonl(tmp_path / "processed" / "personal" / "calendar_events.jsonl", [])
    write_jsonl(tmp_path / "features" / "personal" / "tasks_from_email.jsonl", [])

    briefing = service_for(tmp_path).generate(user_id=user_id)

    assert "chưa có email hoặc lịch" in briefing.morning_report.lower()
    assert briefing.top_priorities == []
    assert briefing.metadata["grounded"] is True


def test_smart_briefing_includes_source_links(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("backend.app.services.llm_service.OllamaService.is_available", lambda self: False)
    user_id = "source-smart"
    write_jsonl(
        tmp_path / "processed" / "personal" / "gmail_messages.jsonl",
        [
            {
                "message_id": "m1",
                "user_id": user_id,
                "from": "teacher@hus.edu.vn",
                "subject": "Deadline báo cáo",
                "snippet": "Hạn nộp trước 17h thứ Sáu",
                "body": "Cần nộp báo cáo.",
                "category": "deadline",
                "priority_hint": "high",
                "expected_task": True,
                "is_unread": True,
                "is_important": True,
                "source_mode": "real",
            }
        ],
    )
    write_jsonl(tmp_path / "processed" / "personal" / "calendar_events.jsonl", [])
    write_jsonl(tmp_path / "features" / "personal" / "tasks_from_email.jsonl", [])

    briefing = service_for(tmp_path).generate(user_id=user_id)

    assert briefing.top_priorities
    assert any(source["source_id"] == "m1" for source in briefing.sources)


def test_chat_today_uses_smart_briefing_metadata() -> None:
    client = TestClient(app)
    headers = user_headers(client)
    response = client.post("/api/assistant/chat", headers=headers, json={"message": "hôm nay tôi cần làm gì", "use_mock_google": True})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "daily_briefing"
    assert "smart_briefing" in body["metadata"]
    assert "context_engine_build" in body["actions"]

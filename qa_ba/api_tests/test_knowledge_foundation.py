from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.context.context_engine import ContextEngine
from backend.app.services.knowledge.knowledge_store import KnowledgeStore
from qa_ba.api_tests.auth_helpers import user_headers


class EmptyTaskStore:
    def list_tasks(self, **kwargs):
        return []


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records), encoding="utf-8")


def test_knowledge_store_creates_nodes_and_edges(tmp_path: Path) -> None:
    user_id = "knowledge-test"
    write_jsonl(
        tmp_path / "processed" / "personal" / "gmail_messages.jsonl",
        [
            {
                "message_id": "m1",
                "user_id": user_id,
                "from": "teacher@hus.edu.vn",
                "subject": "Dự án khai phá dữ liệu",
                "snippet": "Hạn nộp báo cáo trước 17h thứ Sáu",
                "body": "Chuẩn bị báo cáo cho dự án.",
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

    engine = ContextEngine()
    engine.data_root = tmp_path
    engine.task_store = EmptyTaskStore()
    store = KnowledgeStore()
    store.data_root = tmp_path
    store.context_engine = engine

    graph = store.build_from_context(user_id=user_id)
    summary = store.summary(user_id=user_id)

    assert graph.nodes
    assert graph.edges
    assert summary["node_count"] >= 2
    assert "EmailThread" in summary["node_counts"]


def test_knowledge_api_returns_summary() -> None:
    client = TestClient(app)
    headers = user_headers(client)
    response = client.get("/api/knowledge/summary", headers=headers)
    assert response.status_code == 200
    assert "node_count" in response.json()

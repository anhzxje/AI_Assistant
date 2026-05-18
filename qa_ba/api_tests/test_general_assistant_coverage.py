"""Coverage for general-purpose assistant routing."""

from __future__ import annotations

from types import SimpleNamespace
import uuid

from fastapi.testclient import TestClient

from backend.app.main import app


def test_date_time_queries_route_to_local_date_time() -> None:
    for message in ["hôm nay là ngày nào", "bây giờ là mấy giờ"]:
        body = post_chat(message).json()

        assert body["intent"] == "date_time"
        assert body["answer"]
        assert body["metadata"]["general_llm_mode"] == "not_used"


def test_general_questions_route_to_ollama_general_chat(monkeypatch) -> None:
    install_fake_ollama(monkeypatch)
    queries = [
        "giải thích AI là gì",
        "viết giúp tôi email xin nghỉ học",
        "dịch câu này sang tiếng Anh: tôi đang học trí tuệ nhân tạo",
        "code Python đọc file CSV",
        "lập kế hoạch học IELTS trong 2 tuần",
        "tóm tắt đoạn sau: Trí tuệ nhân tạo là lĩnh vực mô phỏng năng lực nhận thức.",
        "hello",
        "bạn là ai",
        "ngành khoa học dữ liệu là gì",
    ]

    for message in queries:
        body = post_chat(message).json()

        assert body["intent"] == "general_chat", message
        assert body["answer"]
        assert not body["sources"]


def test_institutional_questions_route_to_rag(monkeypatch) -> None:
    install_fake_rag(monkeypatch)
    queries = [
        "hiệu trưởng HUS là ai",
        "khoa học dữ liệu ở HUS học những gì",
        "ban giám hiệu trường gồm những ai",
    ]

    for message in queries:
        body = post_chat(message).json()

        assert body["intent"] == "institutional_rag", message
        assert body["answer"]
        assert body["sources"]


def test_personal_and_tool_questions_route_to_tools() -> None:
    expected = {
        "hôm nay tôi cần làm gì": "daily_briefing",
        "tôi có task nào chưa xong": "tasks",
        "tóm tắt email": "gmail",
    }
    for message, intent in expected.items():
        body = post_chat(message).json()

        assert body["intent"] == intent
        assert body["answer"]


def test_clarification_and_fallback_routes() -> None:
    clarification = post_chat("cái đó thì sao?").json()
    fallback = post_chat("asdfgh qwerty zzz").json()

    assert clarification["intent"] == "clarification"
    assert clarification["answer"]
    assert fallback["intent"] == "fallback"
    assert "Mình" in fallback["answer"]


def install_fake_ollama(monkeypatch) -> None:
    from orchestration.nodes import general_chat_node

    class FakeOllama:
        last_latency_ms = 8
        last_error = None

        def is_available(self) -> bool:
            return True

        def generate(self, prompt: str, *, temperature: float = 0.1, num_ctx: int = 4096) -> str:
            return "Đây là câu trả lời tổng quát bằng tiếng Việt."

    monkeypatch.setattr(general_chat_node, "OllamaService", FakeOllama)


def install_fake_rag(monkeypatch) -> None:
    from orchestration.nodes import rag_node

    class Dumpable:
        def __init__(self, **values):
            self.values = values

        def model_dump(self, mode: str = "json"):
            return dict(self.values)

    class FakeAnswerService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def answer(self, **kwargs):
            citation = Dumpable(
                title="Ban Giám hiệu Trường",
                source_url="https://hus.vnu.edu.vn/gioi-thieu/co-cau-to-chuc/ban-giam-hieu",
                document_type="leadership",
                chunk_id="chunk-test",
                score=0.9,
                preview="Nguồn chính thức của HUS.",
            )
            metadata = SimpleNamespace(
                memory_items=0,
                mode="ollama",
                model_dump=lambda mode="json": {"mode": "ollama", "memory_items": 0},
            )
            return SimpleNamespace(
                answer="Câu trả lời HUS có dẫn nguồn [1].",
                citations=[citation],
                debug_retrieval=[citation],
                metadata=metadata,
            )

    monkeypatch.setattr(rag_node, "AnswerService", FakeAnswerService)


def post_chat(message: str):
    client = TestClient(app)
    return client.post(
        "/api/assistant/chat",
        json={
            "user_id": f"test-{uuid.uuid4()}",
            "session_id": f"session-{uuid.uuid4()}",
            "message": message,
            "include_memory": True,
            "use_mock_google": True,
        },
    )

from __future__ import annotations

from pathlib import Path

from backend.app.services.answer_service import contains_suspicious_foreign_fragment
from backend.app.services.auth.user_store import UserStore
from backend.app.services.memory.session_memory import SessionMemory
from data_platform.processing.chunkers.text_chunker import chunk_text


def test_seed_users_include_isolated_second_user(tmp_path: Path) -> None:
    store = UserStore(path=tmp_path / "users.jsonl")
    users = {user.email: user for user in store.list_users()}

    assert set(users) >= {"admin@omni.local", "user@omni.local", "user2@omni.local"}
    assert users["user2@omni.local"].role == "user"
    assert users["user2@omni.local"].display_name == "Người dùng 2"
    assert len({users[email].user_id for email in users}) == len(users)


def test_chunker_prefers_readable_boundaries_and_previews() -> None:
    text = (
        "Khoa học dữ liệu trang bị nền tảng toán học, thống kê và lập trình. "
        "Sinh viên học khai phá dữ liệu, học máy, cơ sở dữ liệu và trực quan hóa dữ liệu. "
        "Chương trình cũng có các học phần thực hành theo dự án để vận dụng kiến thức. "
    ) * 8

    chunks = chunk_text(text, chunk_size=260, chunk_overlap=70, min_chunk_chars=80)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.text == chunk.text.strip()
        assert chunk.preview_text
        assert not chunk.preview_text.endswith("...")
        if chunk.preview_text.endswith("…"):
            assert not chunk.preview_text[-2].isspace()
        if chunk.character_start > 0:
            previous = text.strip()[chunk.character_start - 1]
            assert previous.isspace() or previous in ".?!;:\n"


def test_foreign_language_guard_detects_known_bad_fragment() -> None:
    answer = "Nội dung này có terming dari teknologi, sains bumi dan kehidupan không phù hợp."

    assert contains_suspicious_foreign_fragment(answer.lower())


def test_session_memory_is_scoped_by_user_id() -> None:
    session_memory = SessionMemory()
    session_memory._redis = None

    session_memory.append_turn(user_id="admin-id", session_id="same-session", role="user", content="admin only")
    session_memory.append_turn(user_id="user-id", session_id="same-session", role="user", content="user only")

    admin_turns = session_memory.recent_turns(user_id="admin-id", session_id="same-session")
    user_turns = session_memory.recent_turns(user_id="user-id", session_id="same-session")

    assert [turn["content"] for turn in admin_turns] == ["admin only"]
    assert [turn["content"] for turn in user_turns] == ["user only"]

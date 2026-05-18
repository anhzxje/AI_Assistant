from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_empty_default_conversation_helper_exists() -> None:
    types = (ROOT / "frontend" / "lib" / "types.ts").read_text(encoding="utf-8")
    assert "isMeaningfulConversation" in types
    assert 'message.role === "user"' in types
    assert "hasCustomConversationTitle" in types


def test_sidebar_filters_empty_default_conversations() -> None:
    sidebar = (ROOT / "frontend" / "components" / "chat" / "ConversationSidebar.tsx").read_text(encoding="utf-8")
    assert ".filter(isMeaningfulConversation)" in sidebar


def test_delete_last_visible_creates_hidden_blank_chat() -> None:
    shell = (ROOT / "frontend" / "components" / "chat" / "ChatShell.tsx").read_text(encoding="utf-8")
    assert "remaining.length ? remaining : [createConversation()]" in shell
    assert "current.filter(isMeaningfulConversation)" in shell
    assert "if (!conversation || !isMeaningfulConversation(conversation)) return;" in shell

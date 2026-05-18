from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_frontend_text() -> str:
    files = [
        ROOT / "frontend" / "components" / "brand" / "AppLogo.tsx",
        ROOT / "frontend" / "components" / "brand" / "BrandMark.tsx",
        ROOT / "frontend" / "components" / "chat" / "PromptComposer.tsx",
        ROOT / "frontend" / "components" / "briefing" / "BriefingShell.tsx",
        ROOT / "frontend" / "components" / "briefing" / "BriefingOverview.tsx",
        ROOT / "frontend" / "components" / "briefing" / "GmailPanel.tsx",
        ROOT / "frontend" / "components" / "briefing" / "CalendarPanel.tsx",
        ROOT / "frontend" / "components" / "briefing" / "DemoScenarioPanel.tsx",
    ]
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


def test_product_name_is_lumi() -> None:
    text = read_frontend_text()
    assert 'APP_NAME = "Lumi"' in text
    assert "AI assistant for HUS knowledge, study, and productivity." in text


def test_user_facing_google_wording_avoids_real_literal() -> None:
    text = read_frontend_text()
    banned = [
        "Google thật",
        "Gmail thật",
        "Calendar thật",
        "dữ liệu thật",
        "Real Google",
        "real Google",
        "Đồng bộ Gmail thật",
        "Đồng bộ Calendar thật",
        "Tạo briefing từ dữ liệu thật",
    ]
    for phrase in banned:
        assert phrase not in text

"""Draft-only Action Studio assistant node."""

from __future__ import annotations

from backend.app.services.action_studio.email_draft_generator import EmailDraftGenerator
from backend.app.services.action_studio.meeting_prep import MeetingPrepGenerator
from backend.app.services.action_studio.report_generator import ReportGenerator
from orchestration.assistant_brain import normalize_text


def run(state: dict) -> dict:
    message = str(state.get("message") or "")
    text = normalize_text(message)
    draft = None
    action = "action_studio_draft"
    if contains_any(text, ["bao cao", "report"]):
        period = "7d" if contains_any(text, ["tuan", "week"]) else "today"
        draft = ReportGenerator().generate(user_id=state["user_id"], period=period, role=str(state.get("auth_role") or "user"))
        action = "action_studio_report"
    elif contains_any(text, ["email", "phan hoi", "tra loi", "reply"]):
        draft = EmailDraftGenerator().generate(user_id=state["user_id"], instruction=message)
        action = "action_studio_email_draft"
    else:
        draft = MeetingPrepGenerator().generate(user_id=state["user_id"], query=message)
        action = "action_studio_meeting_prep"
        if draft.draft_type == "exam_prep":
            action = "action_studio_exam_prep"
        elif str(draft.content).startswith("Hôm nay mình chưa thấy"):
            action = "action_studio_clarification"

    state["answer"] = (
        "Đây là bản nháp. Bạn nên kiểm tra lại tên người, thời gian và nội dung trước khi dùng.\n\n"
        f"{draft.content}"
    )
    state["sources"] = draft.sources[:8]
    state["actions"] = [action, "draft_only_no_write"]
    state["metadata"]["action_studio"] = {
        "draft_id": draft.draft_id,
        "draft_type": draft.draft_type,
        "warning": draft.metadata.get("warning"),
        "draft_only": True,
        "no_google_write": True,
    }
    state["memory_used"] = False
    return state


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)

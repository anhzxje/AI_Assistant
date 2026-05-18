"""Copyable email reply draft generator. This never sends or creates Gmail drafts."""

from __future__ import annotations

from .action_schema import ActionDraft
from .action_store import ActionDraftStore
from .source_context_loader import SourceContextLoader


class EmailDraftGenerator:
    def __init__(self) -> None:
        self.loader = SourceContextLoader()
        self.store = ActionDraftStore()

    def generate(
        self,
        *,
        user_id: str,
        email_id: str | None = None,
        thread_id: str | None = None,
        instruction: str = "viết phản hồi lịch sự",
        tone: str = "formal",
        language: str = "vi",
    ) -> ActionDraft:
        bundle = self.loader.load(user_id=user_id, email_id=email_id, thread_id=thread_id)
        email = bundle.selected.get("email")
        if not email:
            content = missing_email_payload(instruction)
            title = "Email draft cần thêm ngữ cảnh"
        else:
            content = email_payload(email=email, instruction=instruction, tone=tone, language=language)
            title = f"Email draft: {email.get('subject') or '(No subject)'}"
        sources = [source.model_dump(mode="json") for source in bundle.sources if source.source_type in {"gmail", "briefing", "knowledge"}][:12]
        return self.store.create(
            user_id=user_id,
            draft_type="email_draft",
            title=title,
            content=content,
            format="json",
            sources=sources,
            metadata={
                "llm_used": False,
                "grounded": True,
                "email_id": email_id,
                "thread_id": thread_id,
                "tone": tone,
                "language": language,
                "no_send": True,
                "no_gmail_draft": True,
            },
        )


def missing_email_payload(instruction: str) -> str:
    return (
        "{\n"
        '  "subject": "Cần thêm email nguồn",\n'
        '  "body": "Mình chưa tìm thấy email nguồn để soạn phản hồi. Vui lòng chọn email hoặc cung cấp nội dung cần trả lời.",\n'
        f'  "notes": "Yêu cầu: {escape_json_text(instruction)}. Đây chỉ là bản nháp, chưa gửi và chưa tạo Gmail draft.",\n'
        '  "sources": []\n'
        "}"
    )


def email_payload(*, email: dict, instruction: str, tone: str, language: str) -> str:
    subject = str(email.get("subject") or "")
    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject or 'Phản hồi'}"
    greeting = "Kính gửi Thầy/Cô," if tone == "formal" and language == "vi" else "Chào anh/chị,"
    body_lines = [
        greeting,
        "",
        "Em cảm ơn Thầy/Cô đã gửi thông tin.",
        "Em đã ghi nhận nội dung và sẽ kiểm tra/chuẩn bị các phần liên quan.",
        "Nếu cần thêm tài liệu hoặc yêu cầu cụ thể, Thầy/Cô vui lòng cho em biết để em hoàn thiện đúng hạn.",
        "",
        "Trân trọng,",
    ]
    if tone == "short":
        body_lines = [greeting, "", "Em cảm ơn Thầy/Cô. Em đã nhận được thông tin và sẽ xử lý sớm.", "", "Trân trọng,"]
    notes = f"Instruction: {instruction}. Source email from {email.get('from') or 'unknown sender'}. Draft only; not sent."
    return (
        "{\n"
        f'  "subject": "{escape_json_text(reply_subject)}",\n'
        f'  "body": "{escape_json_text(chr(10).join(body_lines))}",\n'
        f'  "notes": "{escape_json_text(notes)}",\n'
        f'  "sources": ["gmail:{escape_json_text(str(email.get("message_id") or ""))}"]\n'
        "}"
    )


def escape_json_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


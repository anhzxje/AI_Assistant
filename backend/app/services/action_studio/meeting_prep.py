"""Context-aware meeting and exam preparation draft generator."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from backend.app.services.llm_service import OllamaService
from orchestration.assistant_brain import normalize_text

from .action_schema import ActionDraft
from .action_store import ActionDraftStore
from .context_sanitizer import (
    contains_noisy_artifacts,
    keyword_tokens,
    sanitize_email,
    sanitize_event,
    sanitize_person,
    sanitize_project,
    sanitize_task,
)
from .source_context_loader import SourceContextLoader


MEETING_TERMS = {
    "meeting",
    "seminar",
    "appointment",
    "discussion",
    "interview",
    "defense",
    "consultation",
    "group work",
    "họp",
    "hop",
    "gặp",
    "gap",
    "trao đổi",
    "trao doi",
    "tư vấn",
    "tu van",
    "làm việc nhóm",
    "lam viec nhom",
    "bảo vệ",
    "bao ve",
}
EXAM_TERMS = {"exam", "thi", "lịch thi", "lich thi", "kiểm tra", "kiem tra"}
NON_MEETING_CATEGORIES = {"exam", "deadline", "holiday", "class", "task"}


class MeetingPrepGenerator:
    def __init__(self) -> None:
        self.loader = SourceContextLoader()
        self.store = ActionDraftStore()
        self.llm = OllamaService()

    def generate(
        self,
        *,
        user_id: str,
        query: str,
        event_id: str | None = None,
        project_id: str | None = None,
        include_emails: bool = True,
        include_tasks: bool = True,
    ) -> ActionDraft:
        bundle = self.loader.load(user_id=user_id, event_id=event_id, project_id=project_id)
        query_profile = normalize_text(query)
        query_kind = requested_kind(query_profile)
        selected_raw = bundle.selected.get("event") or select_event(bundle.calendar_events, query_profile=query_profile, query_kind=query_kind)
        selected_kind = event_kind(selected_raw) if selected_raw else query_kind
        event = sanitize_event(selected_raw) if selected_raw else None
        project = sanitize_project(bundle.selected.get("project") or first_project(bundle.context.get("projects", []), project_id))

        if selected_kind == "exam" or (event and event_kind(selected_raw) == "exam"):
            content = exam_prep_content(event, query=query)
            draft_type = "exam_prep"
            title = f"Chuẩn bị lịch thi: {event['summary'] if event else query[:80]}"
            selected_action = "exam_prep"
        elif not event and query_kind == "meeting":
            alternatives = relevant_events(bundle.calendar_events, query_profile=query_profile, limit=5)
            content = no_meeting_content(alternatives)
            draft_type = "meeting_prep"
            title = "Cần chọn cuộc họp"
            selected_action = "clarification_required"
        elif event and event_kind(selected_raw) != "meeting" and query_kind == "meeting":
            alternatives = relevant_events(bundle.calendar_events, query_profile=query_profile, limit=5)
            content = no_meeting_content(alternatives)
            draft_type = "meeting_prep"
            title = "Cần chọn cuộc họp"
            selected_action = "clarification_required"
        else:
            emails = related_emails(bundle.gmail_messages, event=event, query=query, include=include_emails)
            tasks = related_tasks([*bundle.tasks, *bundle.context.get("tasks", [])], event=event, query=query, include=include_tasks)
            people = related_people(bundle.context.get("people", []), emails=emails)
            content = meeting_prep_content(event=event, project=project, emails=emails, tasks=tasks, people=people, query=query)
            polished = polish_if_safe(content)
            llm_used = polished != content
            content = polished
            draft_type = "meeting_prep"
            title = f"Chuẩn bị họp: {event['summary'] if event else query[:80]}"
            selected_action = "meeting_prep"

        sources = source_refs_for(bundle.sources, event=selected_raw, draft_kind=selected_action)
        return self.store.create(
            user_id=user_id,
            draft_type=draft_type,
            title=title,
            content=content,
            format="markdown",
            sources=[source.model_dump(mode="json") for source in sources],
            metadata={
                "llm_used": bool(locals().get("llm_used", False)),
                "grounded": True,
                "query": query,
                "event_id": selected_raw.get("event_id") if selected_raw else None,
                "event_kind": selected_kind,
                "project_id": project.get("project_id") if project else None,
                "warning": "Draft only. Review before use.",
                "no_google_write": True,
            },
        )


def requested_kind(query_profile: str) -> str:
    if any(term in query_profile for term in EXAM_TERMS):
        return "exam"
    if any(term in query_profile for term in MEETING_TERMS):
        return "meeting"
    return "meeting"


def event_kind(event: dict[str, Any] | None) -> str:
    if not event:
        return "unknown"
    text = normalize_text(f"{event.get('summary', '')} {event.get('description', '')} {event.get('category', '')}")
    category = str(event.get("category") or "").lower()
    if category == "exam" or any(term in text for term in EXAM_TERMS):
        return "exam"
    if category in NON_MEETING_CATEGORIES:
        return category
    if category in {"meeting", "seminar"} or any(term in text for term in MEETING_TERMS):
        return "meeting"
    return "event"


def select_event(events: list[dict[str, Any]], *, query_profile: str, query_kind: str) -> dict[str, Any] | None:
    candidates = relevant_events(events, query_profile=query_profile, limit=20)
    if query_kind == "exam":
        typed = [event for event in candidates if event_kind(event) == "exam"]
    else:
        typed = [event for event in candidates if event_kind(event) == "meeting"]
    tokens = keyword_tokens(query_profile)
    if tokens:
        matching = [
            event
            for event in typed
            if tokens.intersection(keyword_tokens(f"{event.get('summary', '')} {event.get('description', '')}"))
        ]
        if matching:
            return matching[0]
        if query_kind == "exam":
            return None
    return typed[0] if typed else None


def relevant_events(events: list[dict[str, Any]], *, query_profile: str, limit: int = 5) -> list[dict[str, Any]]:
    today = date.today()
    wants_today = "hom nay" in query_profile or "hôm nay" in query_profile
    wants_tomorrow = "ngay mai" in query_profile or "ngày mai" in query_profile
    tokens = keyword_tokens(query_profile)
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for event in events:
        try:
            event_date = date.fromisoformat(str(event.get("start_date") or ""))
        except ValueError:
            continue
        if wants_today and event_date != today:
            continue
        if wants_tomorrow and event_date != today.replace(day=today.day) and (event_date - today).days != 1:
            continue
        if event_date < today and "gan nhat" not in query_profile:
            continue
        text = normalize_text(f"{event.get('summary', '')} {event.get('description', '')}")
        match_score = len(tokens.intersection(keyword_tokens(text)))
        type_score = 3 if event_kind(event) == "meeting" else 2 if event_kind(event) == "exam" else 0
        ranked.append((type_score + match_score, f"{event.get('start_date') or ''} {event.get('start_time') or ''}", event))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked[:limit]]


def first_project(projects: list[dict[str, Any]], project_id: str | None) -> dict[str, Any] | None:
    if project_id:
        for project in projects:
            if str(project.get("project_id")) == project_id:
                return project
    for project in projects:
        cleaned = sanitize_project(project)
        if cleaned and float(project.get("score") or 0) >= 1.2:
            return cleaned
    return None


def related_emails(messages: list[dict[str, Any]], *, event: dict[str, Any] | None, query: str, include: bool) -> list[dict[str, Any]]:
    if not include:
        return []
    tokens = keyword_tokens(query, event.get("summary", "") if event else "")
    kept: list[tuple[int, dict[str, Any]]] = []
    for message in messages:
        text = f"{message.get('subject', '')} {message.get('snippet', '')} {message.get('body', '')}"
        if contains_noisy_artifacts(text):
            text = re.sub(r"https?://\S+", "", text)
        overlap = len(tokens.intersection(keyword_tokens(text)))
        if overlap <= 0 and event:
            continue
        if str(message.get("category") or "") in {"promotion", "social", "newsletter", "security"}:
            continue
        kept.append((overlap + int(bool(message.get("is_important"))), sanitize_email(message)))
    kept.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in kept[:5]]


def related_tasks(tasks: list[dict[str, Any]], *, event: dict[str, Any] | None, query: str, include: bool) -> list[dict[str, Any]]:
    if not include:
        return []
    tokens = keyword_tokens(query, event.get("summary", "") if event else "")
    kept: list[tuple[int, dict[str, Any]]] = []
    for task in tasks:
        text = f"{task.get('title', '')} {task.get('source_text', '')}"
        overlap = len(tokens.intersection(keyword_tokens(text)))
        if overlap <= 0 and event:
            continue
        kept.append((overlap + (2 if task.get("priority") == "high" else 0), sanitize_task(task)))
    kept.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in kept[:5]]


def related_people(people: list[dict[str, Any]], *, emails: list[dict[str, Any]]) -> list[dict[str, Any]]:
    email_senders = {str(email.get("sender") or "").lower() for email in emails}
    sanitized = [sanitize_person(person) for person in people]
    matched = [person for person in sanitized if str(person.get("name") or "").lower() in email_senders]
    result = matched or sanitized
    return [person for person in result if person.get("name")][:5]


def meeting_prep_content(
    *,
    event: dict[str, Any] | None,
    project: dict[str, Any] | None,
    emails: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    people: list[dict[str, Any]],
    query: str,
) -> str:
    project = sanitize_project(project)
    event_title = event["summary"] if event else query
    lines = [
        "## Chuẩn bị cuộc họp",
        "",
        f"**Cuộc họp:** {event_title}",
    ]
    if event:
        lines.append(f"**Thời gian:** {event.get('display', '').split(' — ')[0] or 'Chưa rõ'}")
        if event.get("location"):
            lines.append(f"**Địa điểm:** {event['location']}")
    lines.extend(
        [
            "",
            "### 1. Mục tiêu nên chốt",
            f"- Làm rõ kết quả cần đạt của buổi {event_title}.",
            "- Chốt người phụ trách và mốc thời gian cho bước tiếp theo.",
            "",
            "### 2. Bối cảnh ngắn gọn",
        ]
    )
    if project:
        lines.append(f"- Dự án/nhóm việc liên quan: {project.get('name')}.")
    if people:
        lines.append("- Người liên quan: " + ", ".join(person["name"] for person in people[:5]) + ".")
    if emails:
        lines.append("- Có một vài email liên quan cần đọc trước khi họp.")
    if not project and not people and not emails:
        lines.append("- Dữ liệu hiện có chưa cho thấy bối cảnh rõ; nên kiểm tra agenda hoặc tài liệu trước khi họp.")
    lines.extend(["", "### 3. Việc cần chuẩn bị trước"])
    lines.extend([f"- {task['title']}" for task in tasks[:5]] or ["- Kiểm tra lại agenda, tài liệu và thời gian/địa điểm trước khi tham dự."])
    lines.extend(["", "### 4. Câu hỏi nên hỏi"])
    lines.extend(
        [
            "- Mục tiêu quan trọng nhất cần chốt hôm nay là gì?",
            "- Ai phụ trách từng việc sau cuộc họp?",
            "- Deadline hoặc tiêu chí hoàn thành là gì?",
        ]
    )
    if emails:
        lines.append("- Có điểm nào trong email gần đây cần phản hồi hoặc xác nhận không?")
    lines.extend(["", "### 5. Rủi ro cần lưu ý"])
    risks = []
    if not event or not event.get("location"):
        risks.append("- Chưa thấy đầy đủ địa điểm/link họp trong dữ liệu.")
    if not emails:
        risks.append("- Chưa có email/tài liệu liên quan đủ mạnh để suy ra agenda.")
    if not tasks:
        risks.append("- Chưa thấy task liên quan trực tiếp; có thể cần bổ sung việc cần chuẩn bị.")
    lines.extend(risks[:3] or ["- Chưa thấy rủi ro rõ ràng từ dữ liệu hiện có."])
    lines.extend(["", "### 6. Bước tiếp theo sau cuộc họp"])
    lines.extend(["- Ghi lại quyết định chính.", "- Cập nhật task và deadline ngay sau buổi họp.", "", "Đây là bản nháp, bạn nên kiểm tra lại trước khi dùng."])
    return "\n".join(lines)


def exam_prep_content(event: dict[str, Any] | None, *, query: str) -> str:
    subject = event["summary"] if event else query
    lines = [
        "## Chuẩn bị cho lịch thi",
        "",
        f"**Môn:** {subject}",
    ]
    if event:
        lines.append(f"**Thời gian:** {event.get('display', '').split(' — ')[0] or 'Chưa rõ'}")
        if event.get("location"):
            lines.append(f"**Địa điểm:** {event['location']}")
    lines.extend(
        [
            "",
            "### Việc nên làm trước ngày thi",
            "- Ôn các chủ đề chính và dạng bài thường gặp.",
            "- Kiểm tra tài liệu, máy tính hoặc vật dụng được phép mang vào phòng thi.",
            "- Kiểm tra lại phòng thi, thời gian bắt đầu và thời gian có mặt.",
            "- Chuẩn bị giấy tờ cần thiết.",
            "",
            "### Lưu ý",
            "- Đây là lịch thi, nên Lumi dùng cấu trúc ôn tập thay vì agenda trao đổi.",
            "- Nếu bạn muốn, hãy gửi tên môn/chủ đề cần ôn để Lumi lập kế hoạch ôn tập ngắn.",
            "",
            "Đây là bản nháp, bạn nên kiểm tra lại trước khi dùng.",
        ]
    )
    return "\n".join(lines)


def no_meeting_content(events: list[dict[str, Any]]) -> str:
    lines = [
        "Hôm nay mình chưa thấy cuộc họp nào trong lịch.",
        "",
        "Mình thấy các sự kiện sau:",
    ]
    if events:
        lines.extend(f"- {sanitize_event(event)['display']}" for event in events[:5] if sanitize_event(event))
    else:
        lines.append("- Chưa có sự kiện phù hợp trong khoảng thời gian đã đồng bộ.")
    lines.extend(["", "Bạn muốn mình chuẩn bị cho sự kiện nào?"])
    return "\n".join(lines)


def polish_if_safe(content: str) -> str:
    llm = OllamaService()
    if not llm.is_available():
        return content
    prompt = (
        "Bạn là Lumi, trợ lý cá nhân tiếng Việt. Hãy viết lại bản nháp dưới đây cho ngắn, tự nhiên, rõ ý. "
        "Chỉ dùng thông tin có sẵn, không bịa người/sự kiện/email/deadline. Không đưa email, URL, ID nội bộ, "
        "'Google Https', 'Forwarded message' hoặc 'Cài đặt thông báo'. Giữ cấu trúc markdown và độ dài 250-500 từ.\n\n"
        f"BẢN NHÁP:\n{content}"
    )
    generated = llm.generate(prompt, temperature=0.0, num_ctx=2048)
    if not generated or contains_noisy_artifacts(generated):
        return content
    required = ("## Chuẩn bị cuộc họp", "### 1.", "### 2.", "### 3.", "### 4.", "### 5.", "### 6.")
    if any(marker not in generated for marker in required):
        return content
    if "#..." in generated or "..." in generated[:80]:
        return content
    return generated


def strip_llm_marker(content: str) -> str:
    return content


def source_refs_for(sources, *, event: dict[str, Any] | None, draft_kind: str):
    wanted = {"calendar", "task", "briefing", "knowledge"}
    if draft_kind == "meeting_prep":
        wanted.add("gmail")
    kept = []
    selected_id = str(event.get("event_id") or event.get("raw_event_id") or "") if event else ""
    for source in sources:
        if source.source_type not in wanted:
            continue
        if selected_id and source.source_type == "calendar" and source.source_id != selected_id:
            continue
        kept.append(source)
        if len(kept) >= 10:
            break
    return kept

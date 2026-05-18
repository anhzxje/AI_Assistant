"""Marp markdown slide draft generator."""

from __future__ import annotations

from .action_schema import ActionDraft
from .action_store import ActionDraftStore
from .source_context_loader import SourceContextLoader


class SlideGenerator:
    def __init__(self) -> None:
        self.loader = SourceContextLoader()
        self.store = ActionDraftStore()

    def generate(
        self,
        *,
        user_id: str,
        topic: str,
        source: str = "latest_briefing",
        slide_count: int = 6,
        format: str = "marp_markdown",
    ) -> ActionDraft:
        bundle = self.loader.load(user_id=user_id)
        slides = build_slides(topic=topic, slide_count=min(max(slide_count, 3), 12), bundle=bundle)
        return self.store.create(
            user_id=user_id,
            draft_type="slides",
            title=f"Slides: {topic}",
            content=slides,
            format="markdown",
            sources=[source_ref.model_dump(mode="json") for source_ref in bundle.sources[:24]],
            metadata={"llm_used": False, "grounded": True, "source": source, "requested_format": format, "slide_count": slide_count},
        )


def build_slides(*, topic: str, slide_count: int, bundle) -> str:
    priorities = bundle.briefing.get("top_priorities", [])[:4]
    events = bundle.briefing.get("upcoming_events", [])[:4]
    projects = bundle.briefing.get("project_updates", [])[:4]
    emails = bundle.briefing.get("important_emails", [])[:4]
    sections = [
        marp_header(topic),
        title_slide(topic, bundle),
        agenda_slide(),
        context_slide(bundle),
        priorities_slide(priorities),
        timeline_slide(events, emails),
        projects_slide(projects),
        next_steps_slide(priorities, events),
        sources_slide(bundle),
    ]
    if slide_count < len(sections):
        keep = [sections[0], sections[1], sections[2], *sections[3 : max(3, slide_count)], sections[-1]]
        sections = keep[: slide_count + 1]
    return "\n\n---\n\n".join(section.strip() for section in sections if section.strip()) + "\n"


def marp_header(topic: str) -> str:
    return f"---\nmarp: true\ntitle: {topic}\n---"


def title_slide(topic: str, bundle) -> str:
    return f"# {topic}\n\nBản nháp từ Lumi Action Studio\n\n<!-- _notes: Kiểm tra số liệu, tên người và nguồn trước khi trình bày. -->"


def agenda_slide() -> str:
    return "## Agenda\n\n- Bối cảnh\n- Điểm quan trọng\n- Lịch/email liên quan\n- Dự án hoặc đầu việc\n- Bước tiếp theo"


def context_slide(bundle) -> str:
    metadata = bundle.metadata
    return f"## Bối cảnh dữ liệu\n\n- Email đã xử lý: {metadata.get('message_count', 0)}\n- Sự kiện lịch: {metadata.get('event_count', 0)}\n- Task mở: {metadata.get('task_count', 0)}\n- Knowledge graph: {bundle.knowledge_summary.get('node_count', 0)} nodes / {bundle.knowledge_summary.get('edge_count', 0)} edges"


def priorities_slide(priorities) -> str:
    lines = [f"- {item.get('title')}" for item in priorities]
    return "## Điểm cần chú ý\n\n" + "\n".join(lines or ["- Chưa có ưu tiên rõ ràng trong briefing mới nhất."])


def timeline_slide(events, emails) -> str:
    lines = [f"- {event.get('start_date')} {event.get('start_time') or ''}: {event.get('summary')}" for event in events]
    lines.extend(f"- Email: {email.get('subject')}" for email in emails[:2])
    return "## Lịch và email liên quan\n\n" + "\n".join(lines or ["- Chưa có lịch/email liên quan đủ rõ."])


def projects_slide(projects) -> str:
    lines = [f"- {project.get('name')}: {project.get('update_count', 0)} cập nhật" for project in projects]
    return "## Dự án / mạch công việc\n\n" + "\n".join(lines or ["- Chưa phát hiện dự án rõ ràng."])


def next_steps_slide(priorities, events) -> str:
    lines = [f"- {item.get('suggested_action') or item.get('title')}" for item in priorities[:4]]
    if events:
        lines.append("- Chuẩn bị trước các cuộc họp/sự kiện gần nhất.")
    return "## Bước tiếp theo\n\n" + "\n".join(lines or ["- Đồng bộ thêm dữ liệu và cập nhật task trước khi chốt slide."])


def sources_slide(bundle) -> str:
    lines = [f"- {source.source_type}: {source.title}" for source in bundle.sources[:8]]
    return "## Nguồn\n\n" + "\n".join(lines or ["- Chưa có nguồn cụ thể."]) + "\n\n> Đây là bản nháp. Vui lòng kiểm tra trước khi sử dụng."


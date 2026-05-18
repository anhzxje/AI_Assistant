"""Daily and weekly report draft generator."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .action_schema import ActionDraft
from .action_store import ActionDraftStore
from .context_sanitizer import sanitize_email, sanitize_event, sanitize_project, sanitize_task, sanitize_text
from .source_context_loader import SourceContextLoader


class ReportGenerator:
    def __init__(self) -> None:
        self.loader = SourceContextLoader()
        self.store = ActionDraftStore()

    def generate(self, *, user_id: str, period: str = "today", style: str = "student", project_id: str | None = None, role: str = "user") -> ActionDraft:
        bundle = self.loader.load(user_id=user_id, project_id=project_id)
        start, end, label = period_bounds(period)
        events = [event for event in bundle.calendar_events if in_date_range(event.get("start_date"), start, end)]
        emails = bundle.context.get("important_emails", [])[:5]
        tasks = bundle.context.get("tasks", [])[:8]
        projects = [project for project in (sanitize_project(project) for project in bundle.context.get("projects", [])[:8]) if project]
        if project_id:
            projects = [project for project in projects if str(project.get("project_id")) == project_id] or projects

        content = "\n".join(
            [
                "# Báo cáo công việc",
                "",
                "## Tóm tắt",
                summary_line(label, events, emails, tasks, projects, role),
                "",
                "## Việc đã xử lý",
                handled_items(tasks),
                "",
                "## Việc quan trọng / deadline",
                deadline_items(bundle.context.get("deadlines", []), tasks),
                "",
                "## Lịch và cuộc họp",
                event_items(events),
                "",
                "## Email quan trọng",
                email_items(emails),
                "",
                "## Tiến độ theo dự án",
                project_items(projects),
                "",
                "## Rủi ro / blocker",
                blockers(bundle, events, emails, tasks),
                "",
                "## Kế hoạch tiếp theo",
                next_plan(tasks, events),
                "",
                admin_status(role),
                "",
                "> Đây là bản nháp. Vui lòng kiểm tra trước khi sử dụng.",
            ]
        ).strip()
        return self.store.create(
            user_id=user_id,
            draft_type="report",
            title=f"Báo cáo {label}",
            content=content,
            format="markdown",
            sources=[source.model_dump(mode="json") for source in bundle.sources[:24]],
            metadata={"llm_used": False, "grounded": True, "period": period, "style": style, "role": role},
        )


def period_bounds(period: str) -> tuple[date, date, str]:
    today = date.today()
    if period == "30d":
        return today - timedelta(days=30), today, "30 ngày gần đây"
    if period == "7d":
        return today - timedelta(days=7), today, "tuần này"
    return today, today, "hôm nay"


def in_date_range(value: str | None, start: date, end: date) -> bool:
    try:
        parsed = date.fromisoformat(str(value or ""))
    except ValueError:
        return False
    return start <= parsed <= end


def summary_line(label: str, events: list[dict[str, Any]], emails: list[dict[str, Any]], tasks: list[dict[str, Any]], projects: list[dict[str, Any]], role: str) -> str:
    scope = "công việc cá nhân" if role != "admin" else "công việc cá nhân và trạng thái vận hành có sẵn"
    return f"- Báo cáo {label} tập trung vào {scope}: {len(events)} lịch/cuộc họp, {len(emails)} email quan trọng, {len(tasks)} task, {len(projects)} dự án/ngữ cảnh."


def handled_items(tasks: list[dict[str, Any]]) -> str:
    done = [task for task in tasks if task.get("status") == "done"]
    if not done:
        return "- Chưa có task đã xử lý trong nguồn hiện có."
    return "\n".join(f"- {sanitize_task(task).get('title')}" for task in done[:5])


def deadline_items(deadlines: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> str:
    lines = [f"- {sanitize_text(item.get('text') or item.get('title') or item, limit=160)}" for item in deadlines[:5]]
    lines.extend(f"- {sanitize_task(task).get('title')} (hạn: {task.get('due_date')})" for task in tasks if task.get("due_date"))
    return "\n".join(lines[:6] or ["- Chưa thấy deadline rõ ràng trong nguồn hiện có."])


def event_items(events: list[dict[str, Any]]) -> str:
    if not events:
        return "- Không có sự kiện trong kỳ báo cáo."
    cleaned = [event for event in (sanitize_event(event) for event in events[:8]) if event]
    return "\n".join(f"- {event.get('display')}" for event in cleaned)


def email_items(emails: list[dict[str, Any]]) -> str:
    if not emails:
        return "- Không có email quan trọng được đánh dấu trong ngữ cảnh."
    cleaned = [sanitize_email(email) for email in emails[:5]]
    return "\n".join(f"- {email.get('subject')} - {email.get('sender')}" for email in cleaned)


def project_items(projects: list[dict[str, Any]]) -> str:
    if not projects:
        return "- Chưa gom được dự án rõ ràng từ email/lịch/task."
    return "\n".join(f"- {project.get('name')}: {project.get('update_count', 0)} cập nhật" for project in projects[:5])


def blockers(bundle, events: list[dict[str, Any]], emails: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> str:
    gaps = bundle.context.get("knowledge_gaps", [])
    high_tasks = [task for task in tasks if task.get("priority") == "high"]
    lines = [f"- {sanitize_text(gap.get('message'), limit=160)}" for gap in gaps]
    if high_tasks:
        lines.append(f"- Có {len(high_tasks)} task ưu tiên cao cần theo dõi.")
    if not events and not emails:
        lines.append("- Dữ liệu Google còn ít; nên đồng bộ Gmail/Calendar trước khi dùng báo cáo.")
    return "\n".join(lines[:3] or ["- Chưa thấy blocker rõ ràng."])


def next_plan(tasks: list[dict[str, Any]], events: list[dict[str, Any]]) -> str:
    lines = []
    lines.extend(f"- Hoàn tất/cập nhật: {sanitize_task(task).get('title')}" for task in tasks[:5])
    if events:
        lines.append("- Chuẩn bị trước các lịch/cuộc họp sắp tới.")
    return "\n".join(lines or ["- Tiếp tục đồng bộ dữ liệu và cập nhật task sau khi có tiến độ mới."])


def admin_status(role: str) -> str:
    if role != "admin":
        return ""
    return "## Ghi chú vận hành\n- Bản nháp này chưa tự động lấy báo cáo QA/jobs hệ thống; dùng Dashboard/Admin để kiểm tra sâu hơn."

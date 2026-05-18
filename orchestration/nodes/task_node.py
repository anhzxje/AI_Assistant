"""Task memory node."""

from __future__ import annotations

from backend.app.api.memory import get_memory_context_service
from backend.app.services.llm_service import OllamaService


def run(state: dict) -> dict:
    tasks = get_memory_context_service().task_memory.list_tasks(
        user_id=state["user_id"],
        status="open",
        limit=20,
    )
    if not tasks:
        answer = "You have no open tasks in task memory."
    else:
        lines = []
        for task in tasks[:10]:
            due = f" due {task.due_date.isoformat()}" if task.due_date else ""
            lines.append(f"- [{task.priority}] {task.title}{due}")
        answer = "Open tasks:\n" + "\n".join(lines)
        generated = synthesize_tasks(answer)
        if generated:
            answer = f"{generated}\n\n{answer}"
            state["metadata"]["general_llm_mode"] = "ollama"
    state["answer"] = answer
    state["metadata"].setdefault("general_llm_mode", "llm_unavailable")
    state["sources"] = []
    state["actions"] = ["task_memory_read"]
    state["memory_used"] = True
    return state


def synthesize_tasks(task_list: str) -> str | None:
    llm = OllamaService()
    if not llm.is_available():
        return None
    return llm.generate(
        f"""Summarize and prioritize these open tasks in Vietnamese. Do not remove task names.

TASKS:
{task_list}

ANSWER:
""",
        temperature=0.2,
    )

"""Personal memory node."""

from __future__ import annotations

from backend.app.api.memory import get_memory_context_service
from backend.app.services.llm_service import OllamaService
from backend.app.services.memory.memory_extractor import RuleBasedMemoryExtractor


def run(state: dict) -> dict:
    service = get_memory_context_service()
    extractor = RuleBasedMemoryExtractor()
    memories = extractor.extract_memories(state["message"], forced_importance=0.7)
    tasks = extractor.extract_tasks(state["message"])
    saved = []
    indexed_count = 0

    for memory in memories:
        record, indexed = service.remember_text(
            user_id=state["user_id"],
            text=memory.content,
            memory_type=memory.memory_type,
            importance=memory.importance,
            source="assistant_chat",
        )
        saved.append(record)
        indexed_count += int(indexed)

    for task in tasks:
        service.task_memory.add_task(
            user_id=state["user_id"],
            title=task.title,
            due_date=task.due_date,
            priority=task.priority,
            source_text=state["message"],
        )

    if saved or tasks:
        parts = []
        if saved:
            parts.append(f"Saved {len(saved)} memory item(s).")
        if tasks:
            parts.append(f"Extracted {len(tasks)} task(s).")
        state["answer"] = " ".join(parts)
        state["actions"] = ["memory_saved"] + (["task_extracted"] if tasks else [])
    else:
        context = service.build_context(
            user_id=state["user_id"],
            query=state["message"],
            session_id=state.get("session_id"),
            limit=8,
        )
        if context.long_term_memories:
            lines = [f"- {item.content}" for item in context.long_term_memories[:5]]
            fallback = "Relevant remembered facts:\n" + "\n".join(lines)
            state["answer"] = synthesize_memory_answer(state["message"], fallback) or fallback
        else:
            state["answer"] = "No matching long-term memory found yet."
        state["actions"] = ["memory_query"]

    state["sources"] = []
    state["memory_used"] = True
    state["metadata"]["semantic_indexed"] = indexed_count
    return state


def synthesize_memory_answer(query: str, fallback: str) -> str | None:
    llm = OllamaService()
    if not llm.is_available():
        return None
    return llm.generate(
        f"""Answer in Vietnamese using only these remembered facts. If they are not enough, say so.

QUESTION:
{query}

MEMORY_FACTS:
{fallback}

ANSWER:
""",
        temperature=0.2,
    )

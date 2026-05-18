"""Personal memory and task API endpoints."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.schemas.memory_schema import (
    CreateTaskRequest,
    DeleteResponse,
    MemorySummaryResponse,
    MemoryQueryRequest,
    MemoryQueryResponse,
    RememberRequest,
    RememberResponse,
    TaskRecord,
    UpdateTaskRequest,
)
from backend.app.services.memory.memory_context import MemoryContextService
from backend.app.services.memory.memory_extractor import RuleBasedMemoryExtractor
from backend.app.services.auth.auth_service import get_current_user_optional
from backend.app.services.auth.user_store import UserRecord

router = APIRouter(tags=["memory"])


def resolve_user_id(requested_user_id: str, user: UserRecord | None) -> str:
    return user.user_id if user is not None else requested_user_id


@router.post("/api/memory/remember", response_model=RememberResponse)
def remember(
    request: RememberRequest,
    user: UserRecord | None = Depends(get_current_user_optional),
) -> RememberResponse:
    resolved_user_id = resolve_user_id(request.user_id, user)
    extractor = RuleBasedMemoryExtractor()
    memory_service = get_memory_context_service()

    extracted = extractor.extract_memories(
        request.text,
        forced_memory_type=request.memory_type,
        forced_importance=request.importance,
    )
    if not extracted:
        extracted = [
            extractor.extract_memories(
                f"remember {request.text}",
                forced_memory_type=request.memory_type or "fact",
                forced_importance=request.importance,
            )[0]
        ]

    saved = []
    indexed_count = 0
    for item in extracted:
        memory, indexed = memory_service.remember_text(
            user_id=resolved_user_id,
            text=item.content,
            memory_type=item.memory_type,
            importance=item.importance,
            source="explicit",
        )
        saved.append(memory)
        indexed_count += int(indexed)

    tasks = []
    for task in extractor.extract_tasks(request.text):
        tasks.append(
            memory_service.task_memory.add_task(
                user_id=resolved_user_id,
                title=task.title,
                due_date=task.due_date,
                priority=task.priority,
                source_text=request.text,
            )
        )

    if request.session_id:
        memory_service.session_memory.append_turn(
            user_id=resolved_user_id,
            session_id=request.session_id,
            role="user",
            content=request.text,
            metadata={"source": "remember"},
        )

    return RememberResponse(saved_memories=saved, extracted_tasks=tasks, semantic_indexed=indexed_count)


@router.post("/api/memory/query", response_model=MemoryQueryResponse)
def query_memory(
    request: MemoryQueryRequest,
    user: UserRecord | None = Depends(get_current_user_optional),
) -> MemoryQueryResponse:
    resolved_user_id = resolve_user_id(request.user_id, user)
    context = get_memory_context_service().build_context(
        user_id=resolved_user_id,
        query=request.query,
        session_id=request.session_id,
        limit=request.limit,
    )
    return MemoryQueryResponse(
        long_term_memories=context.long_term_memories,
        semantic_memories=context.semantic_memories,
        open_tasks=context.open_tasks,
        recent_turns=context.recent_turns,
    )


@router.get("/api/memory/summary", response_model=MemorySummaryResponse)
def memory_summary(
    user_id: str = "default",
    session_id: str | None = None,
    limit: int = Query(default=8, ge=1, le=30),
    user: UserRecord | None = Depends(get_current_user_optional),
) -> MemorySummaryResponse:
    resolved_user_id = resolve_user_id(user_id, user)
    memory_service = get_memory_context_service()
    recent_turns = (
        memory_service.session_memory.recent_turns(user_id=resolved_user_id, session_id=session_id, limit=limit)
        if session_id
        else []
    )
    recent_memories = memory_service.long_term_memory.list_recent(user_id=resolved_user_id, limit=limit)
    upcoming_tasks = memory_service.task_memory.list_tasks(user_id=resolved_user_id, status=None, limit=limit)
    return MemorySummaryResponse(
        long_term_memories_count=memory_service.long_term_memory.count(user_id=resolved_user_id),
        tasks_count=memory_service.task_memory.count(user_id=resolved_user_id),
        recent_session_count=len(recent_turns),
        storage_mode={
            "session": memory_service.session_memory.status(),
            "long_term": memory_service.long_term_memory.status(),
            "tasks": memory_service.task_memory.status(),
            "semantic": memory_service._semantic_memory.status()
            if memory_service._semantic_memory is not None
            else "lazy",
        },
        recent_memories=recent_memories,
        upcoming_tasks=upcoming_tasks,
    )


@router.delete("/api/memory/{memory_id}", response_model=DeleteResponse)
def delete_memory(
    memory_id: str,
    user_id: str = "default",
    user: UserRecord | None = Depends(get_current_user_optional),
) -> DeleteResponse:
    deleted = get_memory_context_service().long_term_memory.delete(
        memory_id=memory_id,
        user_id=resolve_user_id(user_id, user),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return DeleteResponse(deleted=True, id=memory_id)


@router.get("/api/tasks", response_model=list[TaskRecord])
def list_tasks(
    user_id: str = "default",
    status: str | None = Query(default=None, pattern="^(open|in_progress|done|cancelled)$"),
    limit: int = Query(default=100, ge=1, le=500),
    user: UserRecord | None = Depends(get_current_user_optional),
) -> list[TaskRecord]:
    return get_memory_context_service().task_memory.list_tasks(
        user_id=resolve_user_id(user_id, user),
        status=status,
        limit=limit,
    )


@router.post("/api/tasks", response_model=TaskRecord)
def create_task(
    request: CreateTaskRequest,
    user: UserRecord | None = Depends(get_current_user_optional),
) -> TaskRecord:
    return get_memory_context_service().task_memory.add_task(
        user_id=resolve_user_id(request.user_id, user),
        title=request.title,
        due_date=request.due_date,
        priority=request.priority,
        status=request.status,
        source_text=request.source_text,
        metadata=request.metadata,
    )


@router.patch("/api/tasks/{task_id}", response_model=TaskRecord)
def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    user_id: str = "default",
    user: UserRecord | None = Depends(get_current_user_optional),
) -> TaskRecord:
    updated = get_memory_context_service().task_memory.update_task(
        task_id=task_id,
        user_id=resolve_user_id(user_id, user),
        title=request.title,
        due_date=request.due_date,
        priority=request.priority,
        status=request.status,
        metadata=request.metadata,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.delete("/api/tasks/{task_id}", response_model=DeleteResponse)
def delete_task(
    task_id: str,
    user_id: str = "default",
    user: UserRecord | None = Depends(get_current_user_optional),
) -> DeleteResponse:
    deleted = get_memory_context_service().task_memory.delete_task(
        task_id=task_id,
        user_id=resolve_user_id(user_id, user),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return DeleteResponse(deleted=True, id=task_id)


@lru_cache(maxsize=1)
def get_memory_context_service() -> MemoryContextService:
    return MemoryContextService()

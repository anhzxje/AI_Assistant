"""JSONL storage for draft-only Action Studio outputs."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.config import get_backend_settings
from backend.app.services.connectors.personal_ingestion import read_jsonl

from .action_schema import ActionDraft, DraftFormat, DraftType


DRAFT_WARNING = "Draft only. Review before use."


class ActionDraftStore:
    def __init__(self) -> None:
        self.data_root = get_backend_settings().data_settings.resolved_data_root

    def create(
        self,
        *,
        user_id: str,
        draft_type: DraftType,
        title: str,
        content: str,
        format: DraftFormat,
        sources: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> ActionDraft:
        draft = ActionDraft(
            draft_id=str(uuid.uuid4()),
            user_id=user_id,
            draft_type=draft_type,
            title=title,
            content=content,
            format=format,
            sources=sources,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "llm_used": False,
                "grounded": True,
                "warning": DRAFT_WARNING,
                **(metadata or {}),
            },
        )
        self.save(draft)
        return draft

    def save(self, draft: ActionDraft) -> None:
        folder = self._folder(draft.user_id)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "drafts.jsonl"
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(draft.model_dump(mode="json"), ensure_ascii=False, default=str) + "\n")
        if draft.draft_type == "slides" and draft.format == "markdown":
            slides_dir = folder / "slides"
            slides_dir.mkdir(parents=True, exist_ok=True)
            (slides_dir / f"{draft.draft_id}.md").write_text(draft.content, encoding="utf-8")

    def recent(self, *, user_id: str, limit: int = 20) -> list[ActionDraft]:
        drafts = [ActionDraft.model_validate(item) for item in read_jsonl(self._folder(user_id) / "drafts.jsonl") if item.get("user_id") == user_id]
        drafts.sort(key=lambda item: item.created_at, reverse=True)
        return drafts[:limit]

    def get(self, *, user_id: str, draft_id: str) -> ActionDraft | None:
        for draft in self.recent(user_id=user_id, limit=500):
            if draft.draft_id == draft_id:
                return draft
        return None

    def _folder(self, user_id: str) -> Path:
        safe_user = "".join(ch for ch in user_id if ch.isalnum() or ch in ("-", "_")) or "unknown"
        return self.data_root / "features" / "personal" / "action_studio" / safe_user


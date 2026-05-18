"""JSONL feedback store for assistant quality review."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.schemas.feedback_schema import (
    FeedbackDiagnostics,
    FeedbackRecord,
    FeedbackRequest,
    FeedbackSeverity,
    FeedbackStatus,
)
from data_platform.config import get_settings


HIGH_SEVERITY_REASONS = {"wrong_answer", "missing_source", "outdated_data"}
MEDIUM_SEVERITY_REASONS = {"irrelevant_retrieval", "bad_citation", "bad_asr", "bad_tts", "too_slow"}


class FeedbackStore:
    def __init__(self, path: Path | None = None, feedback_root: Path | None = None) -> None:
        root = feedback_root or get_settings().resolved_data_root / "feedback"
        self.path = path or root / "feedback.jsonl"
        self.root = self.path.parent
        self.root.mkdir(parents=True, exist_ok=True)

    def add_feedback(self, request: FeedbackRequest) -> FeedbackRecord:
        reason = request.reason or "other"
        diagnostics = request.diagnostics or build_feedback_diagnostics(
            answer=request.answer,
            sources=request.sources,
            route=request.route,
        )
        record = FeedbackRecord(
            **request.model_dump(exclude={"reason", "diagnostics"}),
            feedback_id=str(uuid4()),
            reason=reason,
            severity=suggest_severity(reason),
            status="new",
            diagnostics=diagnostics,
            created_at=datetime.now(timezone.utc),
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")
        return record

    def list_feedback(
        self,
        *,
        rating: str | None = None,
        reason: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        intent: str | None = None,
        limit: int = 100,
    ) -> list[FeedbackRecord]:
        records = self._read_all()
        filtered = []
        for record in records:
            if rating and record.rating != rating:
                continue
            if reason and record.reason != reason:
                continue
            if status and record.status != status:
                continue
            if severity and record.severity != severity:
                continue
            if intent and record.intent != intent:
                continue
            filtered.append(record)
        filtered.sort(key=lambda item: item.created_at, reverse=True)
        return filtered[:limit]

    def get_feedback(self, feedback_id: str) -> FeedbackRecord | None:
        for record in self._read_all():
            if record.feedback_id == feedback_id:
                return record
        return None

    def update_feedback(
        self,
        *,
        feedback_id: str,
        status: FeedbackStatus | None = None,
        admin_note: str | None = None,
    ) -> FeedbackRecord | None:
        records = self._read_all()
        updated: FeedbackRecord | None = None
        next_records: list[FeedbackRecord] = []
        for record in records:
            if record.feedback_id == feedback_id:
                data = record.model_dump()
                if status is not None:
                    data["status"] = status
                if admin_note is not None:
                    data["admin_note"] = admin_note
                data["updated_at"] = datetime.now(timezone.utc)
                record = FeedbackRecord.model_validate(data)
                updated = record
            next_records.append(record)
        if updated is None:
            return None
        self._write_all(next_records)
        return updated

    def append_queue_item(self, *, feedback_id: str, queue_name: str) -> tuple[bool, Path]:
        record = self.get_feedback(feedback_id)
        queue_path = self.root / f"{queue_name}.jsonl"
        if record is None:
            return False, queue_path
        payload = {
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "feedback_id": feedback_id,
            "query": record.query,
            "reason": record.reason,
            "intent": record.intent,
            "sources": record.sources,
        }
        with queue_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return True, queue_path

    def summary(self) -> dict[str, Any]:
        records = self._read_all()
        problem_records = [record for record in records if record.rating == "down"]
        source_counter: Counter[str] = Counter()
        query_counter: Counter[str] = Counter()
        for record in problem_records:
            if record.query:
                query_counter[record.query] += 1
            for source in record.sources:
                source_url = source.get("source_url") or source.get("url") or source.get("type")
                if source_url:
                    source_counter[str(source_url)] += 1

        return {
            "total": len(records),
            "by_rating": dict(Counter(record.rating for record in records)),
            "by_status": dict(Counter(record.status for record in records)),
            "by_reason": dict(Counter(record.reason for record in records)),
            "by_severity": dict(Counter(record.severity for record in records)),
            "by_intent": dict(Counter(record.intent or "unknown" for record in records)),
            "top_problem_sources": [
                {"source": source, "count": count} for source, count in source_counter.most_common(10)
            ],
            "top_failed_queries": [
                {"query": query, "count": count} for query, count in query_counter.most_common(10)
            ],
            "recommended_actions": recommended_actions(records),
        }

    def _read_all(self) -> list[FeedbackRecord]:
        if not self.path.exists():
            return []
        records: list[FeedbackRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(parse_feedback_record(line))
            except Exception:
                continue
        return records

    def _write_all(self, records: list[FeedbackRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n")


def parse_feedback_record(line: str) -> FeedbackRecord:
    data = json.loads(line)
    reason = data.get("reason") or "other"
    diagnostics = data.get("diagnostics")
    if diagnostics is None:
        diagnostics = build_feedback_diagnostics(
            answer=str(data.get("answer") or ""),
            sources=data.get("sources") or [],
            route=data.get("route") or [],
        ).model_dump()
    data.setdefault("intent", "")
    data.setdefault("route", [])
    data.setdefault("severity", suggest_severity(reason))
    data.setdefault("admin_note", data.get("admin_note") or "")
    data.setdefault("diagnostics", diagnostics)
    data.setdefault("reason", reason)
    return FeedbackRecord.model_validate(data)


def build_feedback_diagnostics(
    *,
    answer: str,
    sources: list[dict[str, Any]],
    route: list[str],
    latency_ms: int = 0,
) -> FeedbackDiagnostics:
    retrieval_scores = [
        float(source["score"])
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("score"), (int, float))
    ]
    has_citations = "[" in answer and "]" in answer
    suspected_issue = ""
    if "rag_node" in route and not sources:
        suspected_issue = "rag_without_sources"
    elif sources and not has_citations:
        suspected_issue = "missing_citation_marker"
    elif retrieval_scores and max(retrieval_scores) < 0.45:
        suspected_issue = "low_retrieval_score"
    return FeedbackDiagnostics(
        source_count=len(sources),
        has_citations=has_citations,
        latency_ms=latency_ms,
        retrieval_scores=retrieval_scores,
        suspected_issue=suspected_issue,
    )


def suggest_severity(reason: str) -> FeedbackSeverity:
    if reason in HIGH_SEVERITY_REASONS:
        return "high"
    if reason in MEDIUM_SEVERITY_REASONS:
        return "medium"
    return "low"


def recommended_actions(records: list[FeedbackRecord]) -> list[str]:
    reason_counts = Counter(record.reason for record in records if record.rating == "down")
    actions: list[str] = []
    if reason_counts.get("missing_source", 0):
        actions.append("Review missing-source feedback and queue targeted recrawl or source curation.")
    if reason_counts.get("irrelevant_retrieval", 0):
        actions.append("Inspect retrieval scores and queue reindex for repeated irrelevant retrieval reports.")
    if reason_counts.get("outdated_data", 0):
        actions.append("Prioritize fresher institutional source recrawl for outdated-data feedback.")
    if reason_counts.get("bad_citation", 0):
        actions.append("Audit answer citation formatting and citation-source alignment.")
    if not actions:
        actions.append("No urgent feedback cluster detected.")
    return actions


def expected_behavior_for_reason(reason: str) -> str:
    mapping = {
        "missing_source": "should retrieve relevant source",
        "wrong_answer": "should answer using corrected information",
        "outdated_data": "should prefer fresher source",
        "irrelevant_retrieval": "should improve retrieval relevance",
    }
    return mapping.get(reason, "should improve answer quality")


def feedback_record_to_eval_case(record: FeedbackRecord) -> dict[str, Any]:
    return {
        "query": record.query,
        "expected_behavior": expected_behavior_for_reason(record.reason),
        "expected_document_type": None,
        "expected_keywords": expected_keywords(record.correction or record.query),
        "source_feedback_id": record.feedback_id,
        "reason": record.reason,
        "correction": record.correction or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def expected_keywords(value: str) -> list[str]:
    tokens = [token.strip(".,;:!?()[]{}").lower() for token in value.split()]
    return [token for token in tokens if len(token) >= 5][:8]

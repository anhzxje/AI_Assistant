"""MVP drift and staleness detection for data/model monitoring."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from data_platform.config import get_settings


def run_drift_detection() -> dict[str, Any]:
    settings = get_settings()
    chunks = read_latest_jsonl(settings.resolved_data_root / "features" / "chunks", "document_chunks.jsonl")
    documents = read_latest_jsonl(settings.resolved_data_root / "processed" / "documents", "processed_documents.jsonl")
    feedback = read_jsonl(settings.resolved_data_root / "feedback" / "feedback.jsonl")
    retrieval_report = read_json("qa_ba/reports/retrieval_eval_report.json")

    doc_types = Counter(str(row.get("document_type") or "unknown") for row in chunks)
    source_domains = Counter(domain_from_url(str(row.get("source_url") or "")) for row in documents)
    boilerplate_scores = [float((row.get("features") or {}).get("boilerplate_score") or 0.0) for row in chunks]
    production_feedback = [row for row in feedback if not is_synthetic_feedback(row)]
    downvotes = sum(1 for row in production_feedback if row.get("rating") == "down")
    hit_rate = float(retrieval_report.get("document_type_hit_rate") or 0.0)

    signals = []
    if not chunks:
        signals.append(signal("no_chunks", "high", "No feature chunks found; rebuild features and reindex."))
    if doc_types.get("unknown", 0):
        signals.append(signal("unknown_document_type_chunks", "medium", "Review document classifier rules."))
    if average(boilerplate_scores) > 0.35:
        signals.append(signal("boilerplate_increase", "medium", "Review noisy/menu-heavy sources before indexing."))
    if downvotes >= 5:
        signals.append(signal("feedback_downvote_spike", "medium", "Promote feedback to eval and queue targeted data fixes."))
    if retrieval_report and hit_rate < 0.7:
        signals.append(signal("retrieval_hit_rate_drop", "high", "Run retrieval eval, inspect misses, and tune source coverage."))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "review" if signals else "pass",
        "signals": signals,
        "metrics": {
            "document_count": len(documents),
            "chunk_count": len(chunks),
            "document_type_distribution": dict(doc_types),
            "source_domain_distribution": dict(source_domains),
            "average_boilerplate_score": average(boilerplate_scores),
            "feedback_downvotes": downvotes,
            "synthetic_feedback_records": len(feedback) - len(production_feedback),
            "retrieval_hit_rate": hit_rate if retrieval_report else None,
        },
        "mvp_note": "Compares current distributions and QA thresholds. Production can persist historical baselines for statistical drift tests.",
    }


def signal(name: str, severity: str, action: str) -> dict[str, str]:
    return {"name": name, "severity": severity, "recommended_action": action}


def read_latest_jsonl(root: Path, filename: str) -> list[dict[str, Any]]:
    candidates = sorted(root.glob(f"*/{filename}"))
    if not candidates:
        return []
    return read_jsonl(candidates[-1])


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_json(path: str) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


def is_synthetic_feedback(row: dict[str, Any]) -> bool:
    user_id = str(row.get("user_id") or "")
    query = str(row.get("query") or "").lower()
    if user_id.startswith(
        ("test-", "smoke-", "rubric-", "baseline-", "final-", "feedback-eval", "feedback-test")
    ):
        return True
    if user_id.endswith("-smoke") or "smoke" in user_id:
        return True
    if query.startswith(("feedback eval ", "feedback query ")):
        return True
    if query in {"helpful answer", "test", "smoke"} or " smoke " in f" {query} ":
        return True
    if "?" in query and any(marker in query for marker in ("hi?u", "tr??ng", "gi?m")):
        return True
    return False


def domain_from_url(url: str) -> str:
    if "://" not in url:
        return "local_or_unknown"
    return url.split("://", 1)[1].split("/", 1)[0].lower().removeprefix("www.")


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0

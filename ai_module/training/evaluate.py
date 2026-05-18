"""Evaluate the local RAG assistant using existing QA reports."""

from __future__ import annotations

import json
from pathlib import Path

from ai_module.model_registry.registry import write_registry


def evaluate() -> dict:
    reports = Path("qa_ba/reports")
    metrics = {}
    for name in ["retrieval_eval_report.json", "rag_eval_report.json", "feedback_eval_report.json"]:
        path = reports / name
        if path.exists():
            metrics[name] = json.loads(path.read_text(encoding="utf-8"))
    summary = {
        "retrieval_hit_rate": metrics.get("retrieval_eval_report.json", {}).get("document_type_hit_rate"),
        "rag_groundedness": metrics.get("rag_eval_report.json", {}).get("average_groundedness_score"),
        "feedback_pass_rate": metrics.get("feedback_eval_report.json", {}).get("pass_rate"),
        "source_reports": sorted(metrics),
    }
    write_registry({"evaluation_summary": summary, "reports": metrics})
    return summary


if __name__ == "__main__":
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))

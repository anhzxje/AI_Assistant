"""Run lightweight RAG groundedness evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qa_ba.model_eval.evaluate_rag_groundedness import evaluate_rag_groundedness


def main() -> None:
    eval_path = PROJECT_ROOT / "qa_ba" / "test_cases" / "rag_eval_questions.jsonl"
    report_path = PROJECT_ROOT / "qa_ba" / "reports" / "rag_eval_report.json"
    report = evaluate_rag_groundedness(eval_path, top_k=5, use_llm=False)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"rag_eval_report={report_path}")
    print(f"total_cases={report['total_cases']}")
    print(f"average_groundedness_score={report['average_groundedness_score']}")
    print(f"citation_marker_pass_rate={report['citation_marker_pass_rate']}")
    print(f"average_latency_ms={report['average_latency_ms']}")


if __name__ == "__main__":
    main()

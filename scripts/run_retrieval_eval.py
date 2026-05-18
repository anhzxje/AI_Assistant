"""Run retrieval evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qa_ba.model_eval.evaluate_retrieval import evaluate_retrieval


def main() -> None:
    eval_path = PROJECT_ROOT / "qa_ba" / "test_cases" / "rag_eval_questions.jsonl"
    report_path = PROJECT_ROOT / "qa_ba" / "reports" / "retrieval_eval_report.json"
    report = evaluate_retrieval(eval_path, top_k=5)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"retrieval_eval_report={report_path}")
    print(f"total_cases={report['total_cases']}")
    print(f"document_type_hit_rate={report['document_type_hit_rate']}")
    print(f"average_keyword_hit_rate={report['average_keyword_hit_rate']}")
    print(f"average_retrieval_score={report['average_retrieval_score']}")
    print(f"average_latency_ms={report['average_latency_ms']}")


if __name__ == "__main__":
    main()

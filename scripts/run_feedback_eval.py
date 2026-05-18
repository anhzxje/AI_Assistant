"""Run feedback-aware assistant evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qa_ba.model_eval.evaluate_feedback_cases import evaluate_feedback_cases


def main() -> None:
    eval_path = PROJECT_ROOT / "qa_ba" / "test_cases" / "feedback_eval_questions.jsonl"
    report_path = PROJECT_ROOT / "qa_ba" / "reports" / "feedback_eval_report.json"
    report = evaluate_feedback_cases(eval_path, backend_url="http://127.0.0.1:8000")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"feedback_eval_report={report_path}")
    print(f"total_cases={report['total_cases']}")
    print(f"passed_cases={report['passed_cases']}")
    print(f"pass_rate={report['pass_rate']}")
    print(f"average_latency_ms={report['average_latency_ms']}")


if __name__ == "__main__":
    main()

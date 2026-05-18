"""Run MVP data/model drift monitoring."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qa_ba.monitoring.drift_detection import run_drift_detection


def main() -> None:
    report = run_drift_detection()
    report_path = PROJECT_ROOT / "qa_ba" / "reports" / "drift_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"drift_report={report_path}")
    print(f"status={report['status']}")
    print(f"signals={len(report['signals'])}")


if __name__ == "__main__":
    main()

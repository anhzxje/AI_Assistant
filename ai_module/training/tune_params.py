"""MVP parameter tuning for retrieval configuration."""

from __future__ import annotations

import json
from pathlib import Path


def tune() -> dict:
    report_path = Path("qa_ba/reports/retrieval_eval_report.json")
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    hit_rate = float(report.get("document_type_hit_rate") or 0.0)
    config = {
        "top_k": 6 if hit_rate < 0.8 else 5,
        "rerank": True,
        "quality_floor": 0.35,
        "reason": "increase coverage when retrieval hit rate is below target" if hit_rate < 0.8 else "keep default balanced setting",
    }
    output = Path("data/metadata/tuned_retrieval_config.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


if __name__ == "__main__":
    print(json.dumps(tune(), ensure_ascii=False, indent=2))

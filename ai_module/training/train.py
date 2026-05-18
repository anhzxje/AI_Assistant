"""Train/select lightweight assistant configuration."""

from __future__ import annotations

import json
from pathlib import Path

from ai_module.data.feature_loader import load_chunks
from ai_module.model_registry.registry import write_registry


def train() -> dict:
    chunks = load_chunks()
    avg_quality = sum(float((row.get("features") or {}).get("content_quality_score") or 0.0) for row in chunks) / max(len(chunks), 1)
    artifact = {
        "model": "omni-rag-assistant",
        "training_type": "retrieval_prompt_config_selection",
        "chunk_count": len(chunks),
        "average_content_quality_score": round(avg_quality, 4),
        "selected_config": {
            "top_k_simple_fact": 3,
            "top_k_broad": 6,
            "require_citations_for_institutional": True,
        },
    }
    output = Path("data/metadata/training_artifact.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    write_registry({"training_artifact": artifact})
    return artifact


if __name__ == "__main__":
    print(json.dumps(train(), ensure_ascii=False, indent=2))

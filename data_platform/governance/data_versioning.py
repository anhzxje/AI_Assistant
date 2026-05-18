"""DVC-compatible data version metadata."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from data_platform.config import get_settings
from data_platform.governance.hashing import sha256_bytes


def versions_path() -> Path:
    return get_settings().metadata_root / "data_versions.json"


def compute_artifact_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.is_file():
        return sha256_bytes(path.read_bytes())
    entries = []
    for child in sorted(path.rglob("*")):
        if child.is_file():
            entries.append(f"{child.relative_to(path)}:{sha256_bytes(child.read_bytes())}")
    return sha256_bytes("\n".join(entries).encode("utf-8"))


def ensure_data_versions() -> dict[str, Any]:
    settings = get_settings()
    path = versions_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    version = {
        "version": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dvc": {
            "installed": dvc_installed(),
            "note": "Use DVC to track these roots in production; this JSON is the local MVP registry.",
        },
        "artifacts": {
            "raw": {"path": "data/raw", "hash": compute_artifact_hash(settings.resolved_data_root / "raw")},
            "processed": {"path": "data/processed", "hash": compute_artifact_hash(settings.resolved_data_root / "processed")},
            "features": {"path": "data/features", "hash": compute_artifact_hash(settings.resolved_data_root / "features")},
            "metadata": {"path": "data/metadata", "hash": compute_artifact_hash(settings.resolved_data_root / "metadata")},
        },
    }
    path.write_text(json.dumps(version, ensure_ascii=False, indent=2), encoding="utf-8")
    return version


def latest_data_version() -> dict[str, Any]:
    path = versions_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return ensure_data_versions()


def dvc_installed() -> bool:
    try:
        import dvc  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False

"""Mock Google scenario fixtures for local QA and demos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCENARIO_ROOT = Path(__file__).parent / "fixtures" / "scenarios"
DEFAULT_SCENARIO = "student_clean"


def available_scenarios() -> list[str]:
    users = load_scenario_users()
    return [str(item["scenario"]) for item in users]


def load_scenario_users() -> list[dict[str, Any]]:
    path = SCENARIO_ROOT / "users.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def scenario_for_user(user_id: str) -> str | None:
    normalized = user_id.strip().lower()
    for item in load_scenario_users():
        identifiers = {
            str(item.get("user_id") or "").lower(),
            str(item.get("email") or "").lower(),
            str(item.get("seed_user_id") or "").lower(),
        }
        if normalized in identifiers:
            return str(item.get("scenario") or "") or None
    return None


def resolve_scenario(user_id: str, scenario: str | None) -> str | None:
    if scenario:
        candidate = scenario.strip()
        return candidate if scenario_exists(candidate) else None
    return scenario_for_user(user_id)


def scenario_exists(scenario: str) -> bool:
    return (SCENARIO_ROOT / "gmail" / f"{scenario}.json").exists() or (
        SCENARIO_ROOT / "calendar" / f"{scenario}.json"
    ).exists()


def load_gmail_scenario(scenario: str, max_results: int) -> list[dict[str, Any]]:
    path = SCENARIO_ROOT / "gmail" / f"{scenario}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))[:max_results]


def load_calendar_scenario(scenario: str) -> list[dict[str, Any]]:
    path = SCENARIO_ROOT / "calendar" / f"{scenario}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))

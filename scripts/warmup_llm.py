"""Warm up local Ollama through the admin API."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib import request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def post_json(url: str, payload: dict, token: str | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    base_url = "http://127.0.0.1:8000"
    login = post_json(
        f"{base_url}/api/auth/login",
        {"email": "admin@omni.local", "password": "admin123456"},
    )
    result = post_json(f"{base_url}/api/admin/llm/warmup", {}, login["access_token"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Generate a short Vietnamese TTS sample through the local TTS service."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_module.tts.tts_service import TTSService  # noqa: E402


def main() -> None:
    result = TTSService().synthesize(text="Xin chào, mình là Lumi.", language="vi")
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Publication date extraction heuristics."""

from __future__ import annotations

import re
from datetime import date

_DATE_PATTERNS = (
    re.compile(r"(?P<day>\d{1,2})[/-](?P<month>\d{1,2})[/-](?P<year>\d{4})"),
    re.compile(r"ngày\s+(?P<day>\d{1,2})\s+tháng\s+(?P<month>\d{1,2})\s+năm\s+(?P<year>\d{4})", re.I),
)


def extract_published_date(text: str) -> str | None:
    search_area = text[:5000]
    for pattern in _DATE_PATTERNS:
        match = pattern.search(search_area)
        if not match:
            continue
        try:
            parsed = date(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
        except ValueError:
            continue
        return parsed.isoformat()
    return None

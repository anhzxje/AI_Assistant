"""Text normalization helpers for processed documents."""

from __future__ import annotations

import re
import unicodedata

MIN_TEXT_CHARS = 120

_WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_MENU_SPLIT_RE = re.compile(r"\s*(\||/|»|›|•|-{2,})\s*")

BOILERPLATE_TERMS = (
    "một vòng quanh hus",
    "mot vong quanh hus",
    "thông báo - tin tức",
    "thong bao - tin tuc",
    "thông báo tin tức",
    "thong bao tin tuc",
    "ngành học",
    "nganh hoc",
    "tuyển sinh đại học",
    "tuyen sinh dai hoc",
    "đăng nhập",
    "dang nhap",
    "liên hệ",
    "lien he",
    "sơ đồ trang",
    "so do trang",
    "copyright",
    "all rights reserved",
)

CONTENT_TERMS = (
    "hiệu trưởng",
    "hieu truong",
    "phó hiệu trưởng",
    "pho hieu truong",
    "ban giám hiệu",
    "ban giam hieu",
    "lãnh đạo",
    "lanh dao",
    "hội đồng trường",
    "hoi dong truong",
    "chương trình đào tạo",
    "chuong trinh dao tao",
    "học phần",
    "hoc phan",
    "tuyển sinh",
    "tuyen sinh",
    "quy định",
    "quy dinh",
)


def normalize_text(text: str) -> str:
    """Normalize Vietnamese-safe Unicode text and whitespace."""

    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\xa0", " ")
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    lines = [line.strip() for line in normalized.splitlines()]
    lines = [line for line in lines if line]
    return _BLANK_LINES_RE.sub("\n\n", "\n".join(lines)).strip()


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return (
        "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
        .replace("đ", "d")
        .replace("Đ", "D")
        .replace("Ä‘", "d")
        .replace("Ä", "D")
    )


def normalize_for_match(text: str) -> str:
    return strip_accents(normalize_text(text)).lower()


def remove_boilerplate_lines(text: str) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return ""
    lines = normalized.splitlines()
    counts = {line: lines.count(line) for line in set(lines)}
    kept: list[str] = []
    for line in lines:
        if is_boilerplate_line(line, repeated=counts.get(line, 0) >= 3):
            continue
        kept.append(line)
    return normalize_text("\n".join(kept))


def is_boilerplate_line(line: str, *, repeated: bool = False) -> bool:
    compact = " ".join(line.split())
    if not compact:
        return True
    matchable = normalize_for_match(compact)
    word_count = len(matchable.split())
    if repeated and word_count <= 16:
        return True
    if word_count <= 10 and any(term in matchable for term in BOILERPLATE_TERMS):
        return True
    if menu_density_score(compact) > 0.65 and word_count <= 40:
        return True
    if compact.count("http") >= 3:
        return True
    return False


def boilerplate_score(text: str) -> float:
    normalized = normalize_text(text)
    if not normalized:
        return 1.0
    lines = normalized.splitlines()
    if not lines:
        return 1.0
    boilerplate_lines = sum(1 for line in lines if is_boilerplate_line(line))
    score = boilerplate_lines / max(len(lines), 1)
    term_hits = sum(1 for term in BOILERPLATE_TERMS if term in normalize_for_match(normalized))
    return round(min(1.0, score + term_hits * 0.05), 4)


def menu_density_score(text: str) -> float:
    compact = " ".join(str(text or "").split())
    if not compact:
        return 1.0
    matchable = normalize_for_match(compact)
    separators = len(_MENU_SPLIT_RE.findall(compact))
    short_segments = sum(1 for segment in _MENU_SPLIT_RE.split(matchable) if 0 < len(segment.split()) <= 4)
    words = max(len(matchable.split()), 1)
    return round(min(1.0, (separators + short_segments) / max(words / 4, 1)), 4)


def content_quality_score(text: str) -> float:
    normalized = normalize_text(text)
    if not normalized:
        return 0.0
    matchable = normalize_for_match(normalized)
    words = matchable.split()
    length_score = min(1.0, len(words) / 120)
    sentence_score = min(1.0, max(normalized.count("."), normalized.count(":"), normalized.count(";")) / 6)
    content_hits = sum(1 for term in CONTENT_TERMS if term in matchable)
    boilerplate_penalty = boilerplate_score(normalized) * 0.55 + menu_density_score(normalized) * 0.25
    score = 0.35 + length_score * 0.35 + sentence_score * 0.15 + min(content_hits, 4) * 0.05 - boilerplate_penalty
    return round(max(0.0, min(1.0, score)), 4)


def has_enough_text(text: str, min_chars: int = MIN_TEXT_CHARS) -> bool:
    return len(text.strip()) >= min_chars


def detect_language(text: str) -> str:
    """Small heuristic language tagger for Vietnamese institutional documents."""

    lowered = text.lower()
    vietnamese_markers = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    if any(char in lowered for char in vietnamese_markers):
        return "vi"
    ascii_letters = sum(char.isascii() and char.isalpha() for char in text)
    if ascii_letters > 50:
        return "en"
    return "unknown"

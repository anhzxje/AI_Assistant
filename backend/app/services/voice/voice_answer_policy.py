"""Create concise spoken responses from full assistant answers."""

from __future__ import annotations

import re


def build_spoken_answer(answer: str, *, intent: str = "", has_sources: bool = False, max_chars: int = 260) -> str:
    compact = clean_for_speech(answer)
    if not compact:
        return "Mình chưa đủ dữ liệu để khẳng định."

    prefix = "Theo dữ liệu mình tìm được, " if has_sources and intent in {"institutional_rag", "rag"} else ""
    sentences = split_sentences(compact)
    if len(sentences) > 3 or looks_like_long_list(answer):
        summary = summarize_list_answer(sentences, max_chars=max_chars - len(prefix))
        return f"{prefix}{summary} Mình đã tóm tắt ngắn gọn; phần chi tiết mình hiển thị trong khung chat.".strip()

    spoken = " ".join(sentences[:3])
    if len(spoken) > max_chars:
        spoken = truncate_at_word(spoken, max_chars)
        spoken = f"{spoken}. Mình hiển thị thêm chi tiết trong khung chat."
    return f"{prefix}{spoken}".strip()


def clean_for_speech(text: str) -> str:
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^\s*[-*]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -")


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+", text)
    return [piece.strip(" -") for piece in pieces if piece.strip(" -")]


def looks_like_long_list(text: str) -> bool:
    return len(re.findall(r"^\s*[-*]\s+", text, flags=re.MULTILINE)) > 4 or text.count(";") > 4


def summarize_list_answer(sentences: list[str], *, max_chars: int) -> str:
    if not sentences:
        return "mình chưa đủ dữ liệu để khẳng định."
    summary = sentences[0]
    if len(summary) < 80 and len(sentences) > 1:
        summary = f"{summary} {sentences[1]}"
    return truncate_at_word(summary, max_chars).rstrip(".") + "."


def truncate_at_word(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rstrip()
    boundary = clipped.rfind(" ")
    if boundary >= int(max_chars * 0.6):
        clipped = clipped[:boundary]
    return clipped.rstrip(" ,;:")

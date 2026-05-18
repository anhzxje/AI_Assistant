"""Vietnamese-safe document chunking."""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.governance.hashing import sha256_bytes


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str
    character_start: int
    character_end: int
    content_hash: str
    preview_text: str
    context_before: str
    context_after: str


def chunk_text(
    text: str,
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    min_chunk_chars: int = 160,
) -> list[TextChunk]:
    """Split text into overlapping chunks without cutting words when possible."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    stripped = text.strip()
    if len(stripped) < min_chunk_chars:
        return []

    chunks: list[TextChunk] = []
    start = 0
    index = 0
    text_length = len(stripped)

    while start < text_length:
        target_end = min(start + chunk_size, text_length)
        end = _find_natural_boundary(stripped, start, target_end, chunk_size)
        chunk = stripped[start:end].strip()

        if len(chunk) >= min_chunk_chars or (chunks and end == text_length and len(chunk) >= 80):
            actual_start = start + len(stripped[start:end]) - len(stripped[start:end].lstrip())
            actual_end = actual_start + len(chunk)
            chunks.append(
                TextChunk(
                    chunk_index=index,
                    text=chunk,
                    character_start=actual_start,
                    character_end=actual_end,
                    content_hash=sha256_bytes(chunk.encode("utf-8")),
                    preview_text=readable_preview(chunk),
                    context_before=context_window(stripped, actual_start - 360, actual_start),
                    context_after=context_window(stripped, actual_end, actual_end + 360),
                )
            )
            index += 1

        if end >= text_length:
            break
        next_start = max(0, end - chunk_overlap)
        start = _find_overlap_start(stripped, next_start, end)
        if start <= chunks[-1].character_start if chunks else False:
            start = end

    return chunks


def _find_natural_boundary(text: str, start: int, target_end: int, chunk_size: int) -> int:
    if target_end >= len(text):
        return len(text)

    search_start = max(start + int(chunk_size * 0.65), start)
    for delimiter in ("\n\n", "\n", ". ", "? ", "! ", "; ", ": "):
        boundary = text.rfind(delimiter, search_start, target_end)
        if boundary > start:
            return boundary + len(delimiter.rstrip())
    boundary = text.rfind(" ", search_start, target_end)
    if boundary > start:
        return boundary
    return target_end


def _find_overlap_start(text: str, target_start: int, previous_end: int) -> int:
    window_start = max(0, target_start - 180)
    for delimiter in ("\n\n", "\n", ". ", "? ", "! ", "; ", ": "):
        boundary = text.rfind(delimiter, window_start, target_start)
        if boundary >= 0:
            return _advance_to_word_boundary(text, boundary + len(delimiter))
    if target_start < len(text) and target_start > 0 and not text[target_start - 1].isspace() and not text[target_start].isspace():
        while target_start > 0 and not text[target_start - 1].isspace():
            target_start -= 1
    if previous_end - target_start > 260:
        target_start = max(0, previous_end - 260)
    return _advance_to_word_boundary(text, target_start)


def _advance_to_word_boundary(text: str, start: int) -> int:
    while start < len(text) and text[start].isspace():
        start += 1
    return start


def context_window(text: str, start: int, end: int) -> str:
    return " ".join(text[max(0, start) : min(len(text), end)].split())


def readable_preview(text: str, *, limit: int = 360) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    end = _find_preview_end(compact, limit)
    return compact[:end].rstrip(" ,;:") + "…"


def _find_preview_end(text: str, limit: int) -> int:
    floor = int(limit * 0.65)
    for delimiter in (". ", "? ", "! ", "; ", ": "):
        boundary = text.rfind(delimiter, floor, limit)
        if boundary > 0:
            return boundary + 1
    boundary = text.rfind(" ", floor, limit)
    return boundary if boundary > 0 else limit

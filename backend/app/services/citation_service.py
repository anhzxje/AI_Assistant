"""Citation formatting for retrieved chunks."""

from __future__ import annotations

import re

from backend.app.schemas.rag_schema import Citation
from data_platform.feature_store.embeddings.retriever import RetrievalResult


def build_citations(
    results: list[RetrievalResult],
    *,
    answer: str | None = None,
    query: str = "",
    cited_only: bool = True,
) -> list[Citation]:
    cited_indices = citation_indices_from_answer(answer or "")
    citations: list[Citation] = []
    if cited_only and cited_indices:
        indexed_results = [
            (index, result)
            for index, result in enumerate(results, start=1)
            if index in cited_indices
        ]
    elif cited_only:
        indexed_results = [(1, results[0])] if results else []
    else:
        indexed_results = list(enumerate(results, start=1))

    for index, result in indexed_results:
        payload = result.payload
        preview = str(payload.get("preview_text") or "").strip() or readable_preview(result.text)
        snippet = readable_preview(preview or result.text, limit=180)
        used = index in cited_indices or (cited_only and not cited_indices)
        citations.append(
            Citation(
                title=result.title,
                source_url=result.source_url,
                document_type=result.document_type,
                chunk_id=payload.get("chunk_id"),
                score=result.score,
                preview=preview,
                snippet=snippet,
                full_text=payload.get("chunk_text_full") or result.text,
                chunk_text_full=payload.get("chunk_text_full") or result.text,
                preview_text=preview,
                section_heading=payload.get("section_heading"),
                context_before=payload.get("context_before"),
                context_after=payload.get("context_after"),
                usage="cited" if used else "retrieval_debug",
                citation_index=index if used else None,
                relevance_reason=relevance_reason(result, query, used),
                used_in_answer=used,
            )
        )
    return citations


def citation_indices_from_answer(answer: str) -> set[int]:
    return {int(match) for match in re.findall(r"\[(\d+)\]", answer or "")}


def relevance_reason(result: RetrievalResult, query: str, used: bool) -> str:
    normalized_query = query.lower()
    if used:
        return "Cited by the generated answer."
    if result.document_type == "leadership" and any(term in normalized_query for term in ("hiệu trưởng", "hieu truong", "ban giám hiệu", "ban giam hieu")):
        return "Leadership candidate retrieved for entity query."
    return "Retrieved candidate kept for debug review."


def format_context(results: list[RetrievalResult]) -> str:
    blocks: list[str] = []
    for index, result in enumerate(results, start=1):
        text = " ".join(result.text.split())
        blocks.append(
            f"[{index}] Title: {result.title}\n"
            f"Type: {result.document_type}\n"
            f"URL: {result.source_url}\n"
            f"Section: {result.payload.get('section_heading') or ''}\n"
            f"Content: {text[:1400]}"
        )
    return "\n\n".join(blocks)


def readable_preview(text: str, *, limit: int = 360) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    floor = int(limit * 0.65)
    for delimiter in (". ", "? ", "! ", "; ", ": "):
        boundary = compact.rfind(delimiter, floor, limit)
        if boundary > 0:
            return compact[: boundary + 1].rstrip() + "…"
    boundary = compact.rfind(" ", floor, limit)
    if boundary > 0:
        return compact[:boundary].rstrip(" ,;:") + "…"
    return compact[:limit].rstrip(" ,;:") + "…"

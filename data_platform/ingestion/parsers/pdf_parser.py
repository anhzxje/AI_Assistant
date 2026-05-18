"""Raw PDF parser with a PyMuPDF backend."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from data_platform.processing.cleaners.text_cleaner import normalize_text


@dataclass(frozen=True)
class ParsedPdf:
    title: str | None
    text: str
    page_count: int
    pages: list[dict[str, object]]
    metadata: dict[str, object]


class PdfParserUnavailable(RuntimeError):
    """Raised when no supported PDF backend is installed."""


def parse_pdf_file(path: Path) -> ParsedPdf:
    try:
        import fitz  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        return _parse_with_pypdf(path, exc)

    document = fitz.open(path)
    pages: list[dict[str, object]] = []
    all_text: list[str] = []

    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        page_text = normalize_text(page.get_text("text"))
        pages.append(
            {
                "page_number": page_index + 1,
                "text": page_text,
                "char_count": len(page_text),
            }
        )
        if page_text:
            all_text.append(f"[page {page_index + 1}]\n{page_text}")

    metadata = dict(document.metadata or {})
    title = metadata.get("title") if isinstance(metadata.get("title"), str) else None
    return ParsedPdf(
        title=normalize_text(title) if title else None,
        text=normalize_text("\n\n".join(all_text)),
        page_count=document.page_count,
        pages=pages,
        metadata=metadata,
    )


def _parse_with_pypdf(path: Path, original_exc: ModuleNotFoundError) -> ParsedPdf:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise PdfParserUnavailable(
            "PDF parsing requires PyMuPDF or pypdf. Install with `pip install pymupdf`."
        ) from original_exc or exc

    reader = PdfReader(str(path))
    pages: list[dict[str, object]] = []
    all_text: list[str] = []
    for page_index, page in enumerate(reader.pages):
        page_text = normalize_text(page.extract_text() or "")
        pages.append(
            {
                "page_number": page_index + 1,
                "text": page_text,
                "char_count": len(page_text),
            }
        )
        if page_text:
            all_text.append(f"[page {page_index + 1}]\n{page_text}")

    raw_metadata = reader.metadata or {}
    metadata = {str(key).lstrip("/"): str(value) for key, value in raw_metadata.items()}
    title = metadata.get("Title")
    return ParsedPdf(
        title=normalize_text(title) if title else None,
        text=normalize_text("\n\n".join(all_text)),
        page_count=len(reader.pages),
        pages=pages,
        metadata=metadata,
    )

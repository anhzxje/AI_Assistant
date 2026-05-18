"""Raw HTML parser for institutional documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.exceptions import FeatureNotFound

from data_platform.processing.cleaners.text_cleaner import remove_boilerplate_lines, normalize_text
from data_platform.processing.extractors.image_fact_overrides import get_image_fact_text


@dataclass(frozen=True)
class ParsedHtml:
    title: str | None
    text: str
    headings: list[str]
    tables: list[list[list[str]]]
    links: list[dict[str, str]]


def parse_html_file(path: Path, source_url: str | None = None) -> ParsedHtml:
    html = path.read_bytes()
    soup = _make_soup(html)

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    for selector in ("nav", "footer", "header", "aside"):
        for tag in soup.find_all(selector):
            tag.decompose()
    for tag in soup.find_all(attrs={"role": ["navigation", "banner", "contentinfo", "complementary"]}):
        tag.decompose()
    boilerplate_tags = []
    for tag in soup.find_all(True):
        identity = _tag_identity(tag)
        if any(token in identity for token in ("menu", "navbar", "navigation", "breadcrumb", "footer", "header", "sidebar", "widget")):
            boilerplate_tags.append(tag)
    for tag in boilerplate_tags:
        tag.decompose()

    title = None
    if soup.title and soup.title.string:
        title = normalize_text(soup.title.string)

    main = _select_main_content(soup)

    headings = [
        normalize_text(heading.get_text(" ", strip=True))
        for heading in main.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    ]
    headings = [heading for heading in headings if heading]

    tables = [_extract_table(table) for table in main.find_all("table")]
    tables = [table for table in tables if table]

    links: list[dict[str, str]] = []
    for anchor in main.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        text = normalize_text(anchor.get_text(" ", strip=True))
        if not href:
            continue
        links.append(
            {
                "text": text,
                "url": urljoin(source_url or "", href),
            }
        )

    image_urls = [
        urljoin(source_url or "", str(image.get("src", "")).strip())
        for image in main.find_all("img", src=True)
        if str(image.get("src", "")).strip()
    ]
    text = remove_boilerplate_lines(main.get_text("\n", strip=True))
    image_fact_text = get_image_fact_text(source_url or "", image_urls)
    if image_fact_text:
        text = normalize_text("\n".join(part for part in (text, image_fact_text) if part))
    return ParsedHtml(title=title, text=text, headings=headings, tables=tables, links=links)


def _make_soup(html: bytes) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml", from_encoding="utf-8")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser", from_encoding="utf-8")


def _select_main_content(soup: BeautifulSoup) -> object:
    direct = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
    if direct and len(direct.get_text(" ", strip=True)) >= 120:
        return direct

    candidates: list[tuple[int, object]] = []
    positive_tokens = (
        "detailpage",
        "main-content",
        "content",
        "article",
        "post-container",
        "world-latest-articles",
    )
    negative_tokens = ("menu", "navbar", "navtop", "footer", "header")

    for tag in soup.find_all(["section", "div"]):
        identity = _tag_identity(tag)
        text_length = len(tag.get_text(" ", strip=True))
        if text_length < 120:
            continue
        if any(token in identity for token in negative_tokens):
            continue
        score = text_length
        if any(token in identity for token in positive_tokens):
            score += 1000
        candidates.append((score, tag))

    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    return soup.body or soup


def _tag_identity(tag: object) -> str:
    if not getattr(tag, "attrs", None):
        return ""
    tag_id = tag.get("id")  # type: ignore[attr-defined]
    tag_class = tag.get("class")  # type: ignore[attr-defined]
    class_text = " ".join(tag_class) if isinstance(tag_class, list) else tag_class
    return " ".join(str(value) for value in (tag_id, class_text) if value).lower()


def _extract_table(table_tag: object) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table_tag.find_all("tr"):  # type: ignore[attr-defined]
        cells = [
            normalize_text(cell.get_text(" ", strip=True))
            for cell in row.find_all(["th", "td"])
        ]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)
    return rows

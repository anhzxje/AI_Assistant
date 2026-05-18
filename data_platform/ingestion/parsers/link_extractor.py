"""HTML link and title extraction for seed crawling."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.exceptions import FeatureNotFound


@dataclass(frozen=True)
class HtmlLinks:
    title: str | None
    links: tuple[str, ...]


def extract_title_and_links(
    html: bytes,
    base_url: str,
    *,
    from_encoding: str | None = "utf-8",
) -> HtmlLinks:
    """Extract a page title and absolute href links from HTML bytes."""

    try:
        soup = BeautifulSoup(html, "lxml", from_encoding=from_encoding)
    except FeatureNotFound:
        soup = BeautifulSoup(html, "html.parser", from_encoding=from_encoding)

    title: str | None = None
    if soup.title and soup.title.string:
        title = " ".join(soup.title.string.split())

    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        links.append(urljoin(base_url, href))

    return HtmlLinks(title=title, links=tuple(dict.fromkeys(links)))

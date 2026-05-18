"""Allowlisted seed crawler for institutional HUS data sources."""

from __future__ import annotations

import logging
import mimetypes
import shutil
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib import robotparser
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

from data_platform.config import Settings
from data_platform.governance.hashing import sha256_bytes, sha256_file
from data_platform.governance.manifest import CrawlManifestRecord, JsonlManifestWriter
from data_platform.ingestion.connectors.http_client import HttpClient
from data_platform.ingestion.parsers.link_extractor import extract_title_and_links

logger = logging.getLogger(__name__)

PDF_SUFFIX = ".pdf"


@dataclass(frozen=True)
class QueuedUrl:
    url: str
    depth: int
    parent_url: str | None = None


@dataclass
class CrawlStats:
    pages_fetched: int = 0
    pdfs_downloaded: int = 0
    pdfs_copied: int = 0
    skipped_urls: int = 0
    errors: int = 0
    manifest_path: Path | None = None
    skipped_reasons: dict[str, int] = field(default_factory=dict)

    def add_skip(self, reason: str) -> None:
        self.skipped_urls += 1
        self.skipped_reasons[reason] = self.skipped_reasons.get(reason, 0) + 1


class SeedCrawler:
    """Crawl a small institutional seed set into immutable raw storage."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.allowed_domains = set(settings.allowed_domains)
        self.crawl_date = datetime.now(timezone.utc).date().isoformat()
        self.manifest_path = settings.metadata_root / "crawl_manifest.jsonl"
        self.manifest = JsonlManifestWriter(self.manifest_path)
        self.robots: dict[str, robotparser.RobotFileParser] = {}
        self.seen_hashes: set[str] = set()

    def crawl(
        self,
        *,
        seed_file: Path,
        max_depth: int,
        max_pages: int,
        local_pdf_dir: Path | None = None,
    ) -> CrawlStats:
        stats = CrawlStats(manifest_path=self.manifest_path)
        self._ensure_storage_dirs()

        if local_pdf_dir is not None:
            stats.pdfs_copied += self.copy_local_pdfs(local_pdf_dir)

        seeds = self.read_seed_urls(seed_file)
        queue: deque[QueuedUrl] = deque(QueuedUrl(url=seed, depth=0) for seed in seeds)
        seen_urls: set[str] = set()

        with HttpClient(
            user_agent=self.settings.crawl_user_agent,
            timeout_seconds=self.settings.crawl_timeout_seconds,
            max_retries=self.settings.crawl_max_retries,
        ) as http_client:
            while queue and stats.pages_fetched < max_pages:
                item = queue.popleft()
                normalized_url = normalize_url(item.url)

                if normalized_url in seen_urls:
                    stats.add_skip("duplicate_url")
                    continue
                seen_urls.add(normalized_url)

                if not self.is_allowed_domain(normalized_url):
                    stats.add_skip("domain_not_allowed")
                    continue

                if self.settings.respect_robots_txt and not self.is_allowed_by_robots(
                    normalized_url
                ):
                    stats.add_skip("robots_disallowed")
                    self._write_skip_record(normalized_url, item, "robots_disallowed")
                    continue

                try:
                    response = http_client.get(normalized_url)
                except Exception as exc:  # noqa: BLE001 - manifest should capture full crawl failures.
                    logger.warning("Failed to fetch %s: %s", normalized_url, exc)
                    stats.errors += 1
                    self._write_error_record(normalized_url, item, exc)
                    continue

                content_type = response.content_type.lower()
                final_url = normalize_url(response.url)

                if response.status_code >= 400:
                    reason = f"http_status_{response.status_code}"
                    stats.add_skip(reason)
                    self._write_skip_record(
                        final_url,
                        item,
                        reason,
                        response.status_code,
                        content_type,
                    )
                    continue

                is_pdf = looks_like_pdf(final_url, content_type)

                if is_pdf:
                    if self._save_pdf(final_url, item, response.content, content_type, response.status_code):
                        stats.pdfs_downloaded += 1
                    continue

                if not is_html(content_type):
                    stats.add_skip("unsupported_content_type")
                    self._write_skip_record(
                        final_url,
                        item,
                        "unsupported_content_type",
                        response.status_code,
                        content_type,
                    )
                    continue

                title, links = self._save_html(
                    final_url,
                    item,
                    response.content,
                    content_type,
                    response.status_code,
                )
                stats.pages_fetched += 1
                logger.info("Fetched page depth=%s title=%r url=%s", item.depth, title, final_url)

                if item.depth >= max_depth:
                    continue

                for link in links:
                    normalized_link = normalize_url(link)
                    if normalized_link not in seen_urls and self.is_allowed_domain(normalized_link):
                        queue.append(
                            QueuedUrl(
                                url=normalized_link,
                                depth=item.depth + 1,
                                parent_url=final_url,
                            )
                        )
                    else:
                        stats.add_skip("link_not_queued")

        return stats

    def read_seed_urls(self, seed_file: Path) -> tuple[str, ...]:
        lines = seed_file.read_text(encoding="utf-8").splitlines()
        urls = [normalize_url(line.strip()) for line in lines if line.strip()]
        return tuple(dict.fromkeys(urls))

    def copy_local_pdfs(self, local_pdf_dir: Path) -> int:
        copied = 0
        self.seen_hashes.update(self._existing_pdf_hashes())
        for pdf_path in sorted(local_pdf_dir.resolve().glob("*.pdf")):
            content_hash = sha256_file(pdf_path)
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)

            destination = self._unique_path(self.settings.raw_pdf_root / self.crawl_date / pdf_path.name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, destination)
            copied += 1

            self.manifest.append(
                CrawlManifestRecord(
                    url=pdf_path.as_uri(),
                    crawl_time=utc_now_iso(),
                    status="copied_local_pdf",
                    depth=0,
                    content_type="application/pdf",
                    title=pdf_path.stem,
                    saved_path=str(destination.relative_to(self.settings.resolved_project_root)),
                    content_hash=content_hash,
                    source="local_seed_pdf",
                )
            )
        return copied

    def is_allowed_domain(self, url: str) -> bool:
        hostname = urlparse(url).hostname
        return hostname in self.allowed_domains

    def is_allowed_by_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.hostname:
            return False
        parser = self.robots.get(parsed.hostname)
        if parser is None:
            robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
            parser = robotparser.RobotFileParser()
            parser.set_url(robots_url)
            try:
                parser.read()
            except Exception as exc:  # noqa: BLE001 - conservative fallback is to allow and log.
                logger.info("Could not read robots.txt for %s: %s", parsed.hostname, exc)
                return True
            self.robots[parsed.hostname] = parser
        return parser.can_fetch(self.settings.crawl_user_agent, url)

    def _save_html(
        self,
        url: str,
        item: QueuedUrl,
        content: bytes,
        content_type: str,
        status_code: int,
    ) -> tuple[str | None, tuple[str, ...]]:
        content_hash = sha256_bytes(content)
        title_links = extract_title_and_links(
            content,
            url,
            from_encoding=charset_from_content_type(content_type),
        )
        destination = self._html_path(url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

        self.manifest.append(
            CrawlManifestRecord(
                url=url,
                crawl_time=utc_now_iso(),
                status="fetched_html",
                depth=item.depth,
                parent_url=item.parent_url,
                status_code=status_code,
                content_type=content_type,
                title=title_links.title,
                saved_path=str(destination.relative_to(self.settings.resolved_project_root)),
                content_hash=content_hash,
            )
        )
        return title_links.title, title_links.links

    def _save_pdf(
        self,
        url: str,
        item: QueuedUrl,
        content: bytes,
        content_type: str,
        status_code: int,
    ) -> bool:
        content_hash = sha256_bytes(content)
        if content_hash in self.seen_hashes:
            self._write_skip_record(url, item, "duplicate_content", status_code, content_type)
            return False
        self.seen_hashes.add(content_hash)

        destination = self._unique_path(self.settings.raw_pdf_root / self.crawl_date / safe_pdf_name(url))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

        self.manifest.append(
            CrawlManifestRecord(
                url=url,
                crawl_time=utc_now_iso(),
                status="downloaded_pdf",
                depth=item.depth,
                parent_url=item.parent_url,
                status_code=status_code,
                content_type=content_type or "application/pdf",
                title=Path(urlparse(url).path).name,
                saved_path=str(destination.relative_to(self.settings.resolved_project_root)),
                content_hash=content_hash,
            )
        )
        return True

    def _write_error_record(self, url: str, item: QueuedUrl, exc: Exception) -> None:
        self.manifest.append(
            CrawlManifestRecord(
                url=url,
                crawl_time=utc_now_iso(),
                status="error",
                depth=item.depth,
                parent_url=item.parent_url,
                error=repr(exc),
            )
        )

    def _write_skip_record(
        self,
        url: str,
        item: QueuedUrl,
        reason: str,
        status_code: int | None = None,
        content_type: str | None = None,
    ) -> None:
        self.manifest.append(
            CrawlManifestRecord(
                url=url,
                crawl_time=utc_now_iso(),
                status=f"skipped:{reason}",
                depth=item.depth,
                parent_url=item.parent_url,
                status_code=status_code,
                content_type=content_type,
            )
        )

    def _html_path(self, url: str) -> Path:
        parsed = urlparse(url)
        domain = parsed.hostname or "unknown-domain"
        path = parsed.path.strip("/")
        safe_path = safe_url_path(path) if path else "root"
        return self.settings.raw_web_root / self.crawl_date / domain / safe_path / "index.html"

    def _unique_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 2
        while True:
            candidate = parent / f"{stem}-{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _ensure_storage_dirs(self) -> None:
        for directory in (
            self.settings.raw_web_root,
            self.settings.raw_pdf_root,
            self.settings.metadata_root,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def _existing_pdf_hashes(self) -> set[str]:
        pdf_root = self.settings.raw_pdf_root / self.crawl_date
        if not pdf_root.exists():
            return set()
        return {sha256_file(path) for path in pdf_root.glob("*.pdf")}


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = quote(parsed.path or "/", safe="/:%")
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    query = urlencode(sorted(query_pairs), doseq=True)
    normalized = urlunparse((scheme, netloc, path, "", query, ""))
    if normalized.endswith("/") and path != "/":
        normalized = normalized.rstrip("/")
    return normalized


def looks_like_pdf(url: str, content_type: str) -> bool:
    path = urlparse(url).path.lower()
    return "application/pdf" in content_type.lower() or path.endswith(PDF_SUFFIX)


def is_html(content_type: str) -> bool:
    lowered = content_type.lower()
    return "text/html" in lowered or "application/xhtml+xml" in lowered


def charset_from_content_type(content_type: str) -> str | None:
    for part in content_type.split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name.lower() == "charset":
            return value.strip() or None
    return "utf-8"


def safe_url_path(path: str) -> str:
    safe = path.replace("\\", "/").strip("/")
    safe = safe.replace("/", "__")
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in safe)
    return safe[:180] or "root"


def safe_pdf_name(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name or "document.pdf"
    guessed_extension = Path(name).suffix or mimetypes.guess_extension("application/pdf") or ".pdf"
    if not name.lower().endswith(".pdf"):
        name = f"{Path(name).stem}{guessed_extension}"
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in name)
    return safe[:180] or "document.pdf"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

"""Run the allowlisted institutional seed crawl."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_platform.config import get_settings
from data_platform.ingestion.crawlers.seed_crawler import SeedCrawler
from data_platform.logging_utils import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl HUS seed sources into raw storage.")
    parser.add_argument("--depth", type=int, default=None, help="Maximum crawl depth.")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum HTML pages to fetch.")
    parser.add_argument(
        "--seed-file",
        type=Path,
        default=None,
        help="Path to seed_sources.txt.",
    )
    parser.add_argument(
        "--local-pdf-dir",
        type=Path,
        default=Path("../Agent_Knowledge_Base/crawl"),
        help="Directory containing local seed PDFs to copy into raw storage.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    seed_file = args.seed_file or settings.seed_sources_path
    max_depth = args.depth if args.depth is not None else settings.crawl_max_depth

    crawler = SeedCrawler(settings)
    stats = crawler.crawl(
        seed_file=seed_file,
        max_depth=max_depth,
        max_pages=args.max_pages,
        local_pdf_dir=args.local_pdf_dir,
    )

    print("Seed crawl complete")
    print(f"pages_fetched={stats.pages_fetched}")
    print(f"pdfs_downloaded={stats.pdfs_downloaded}")
    print(f"pdfs_copied={stats.pdfs_copied}")
    print(f"skipped_urls={stats.skipped_urls}")
    print(f"errors={stats.errors}")
    print(f"manifest_path={stats.manifest_path}")
    if stats.skipped_reasons:
        print(f"skipped_reasons={stats.skipped_reasons}")


if __name__ == "__main__":
    main()

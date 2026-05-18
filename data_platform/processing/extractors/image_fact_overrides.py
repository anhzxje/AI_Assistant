"""Audited text fallbacks for official image-only institutional pages.

These overrides are intentionally narrow. They are used when an official page
stores critical facts inside an image and the local pipeline has no OCR engine.
Each fact must name the source image so admins can verify it.
"""

from __future__ import annotations

from urllib.parse import urlparse


_HUS_BOARD_IMAGE_URL = "https://hus.vnu.edu.vn/Portals/0/WEB-DATA/images/BGH.png"

_IMAGE_FACTS: dict[str, dict[str, str]] = {
    "https://hus.vnu.edu.vn/gioi-thieu/co-cau-to-chuc/ban-giam-hieu": {
        "image_url": _HUS_BOARD_IMAGE_URL,
        "text": "\n".join(
            [
                "Ban Giám hiệu Trường Đại học Khoa học Tự nhiên - Đại học Quốc gia Hà Nội.",
                "Nguồn chính thức là hình ảnh BGH.png trên trang Ban Giám Hiệu Trường.",
                "GS.TS. Lê Thanh Sơn - Hiệu trưởng.",
                "PGS.TS. Ngạc An Bang - Phó Hiệu trưởng.",
                "PGS.TS. Trần Quốc Bình - Phó Hiệu trưởng.",
                "PGS.TS. Trần Mạnh Cường - Phó Hiệu trưởng.",
            ]
        ),
    },
}


def get_image_fact_text(source_url: str, image_urls: list[str]) -> str:
    normalized_source = _normalize_url(source_url)
    facts = _IMAGE_FACTS.get(normalized_source)
    if not facts:
        return ""
    normalized_images = {_normalize_url(url) for url in image_urls}
    if _normalize_url(facts["image_url"]) not in normalized_images:
        return ""
    return facts["text"]


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{netloc}{path}"

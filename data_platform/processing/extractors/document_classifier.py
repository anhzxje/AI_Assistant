"""Heuristic document classification for HUS institutional data."""

from __future__ import annotations

from collections.abc import Iterable

from data_platform.processing.cleaners.text_cleaner import normalize_for_match

DOCUMENT_TYPES = {
    "announcement",
    "curriculum",
    "lecturer_profile",
    "admission",
    "regulation",
    "program",
    "leadership",
    "department",
    "quality_assurance",
    "general_info",
    "organization",
    "contact",
    "error_page",
    "unknown",
}


def classify_document(*, url: str | None, title: str | None, text: str) -> str:
    url_title = normalize_for_match(" ".join(value or "" for value in (url, title)))
    text_sample = normalize_for_match(text[:4000])
    haystack = normalize_for_match(" ".join(value or "" for value in (url, title, text[:4000])))

    if contains_any(haystack, ("404 error page", "page you are looking for cannot be found")):
        return "error_page"
    if contains_any(url_title, ("thong-bao", "tin-tuc")) or normalize_for_match(str(title or "")) in {"thong bao", "tin tuc"}:
        return "announcement"
    if "tuyensinh.hus.vnu.edu.vn" in url_title and "/nganh-hoc/" in url_title:
        return "admission"
    if url_title.rstrip("/") in {"https://tuyensinh.hus.vnu.edu.vn", "http://tuyensinh.hus.vnu.edu.vn", "tuyensinh.hus.vnu.edu.vn"}:
        return "admission"
    if contains_any(url_title, ("hieu truong", "pho hieu truong", "ban giam hieu", "lanh dao", "hoi dong truong", "co cau to chuc")):
        return "leadership"
    if "ban giam hieu" in text_sample and contains_any(text_sample, ("hieu truong", "pho hieu truong")):
        return "leadership"
    if contains_any(url_title, ("can-bo", "danh-sach-can-bo")) or contains_any(haystack, ("danh sach can bo", "giang vien", "hoc ham", "hoc vi")):
        return "lecturer_profile"
    if normalize_for_match(str(title or "")) == "dao tao" or url_title.rstrip("/").endswith("dao-tao"):
        return "general_info"
    if contains_any(url_title, ("dam-bao-chat-luong", "ba-cong-khai")) or contains_any(haystack, ("dam bao chat luong", "ba cong khai")):
        return "quality_assurance"
    if contains_any(url_title, ("phong-ban-chuc-nang", "phong dao tao", "lien-he")) or contains_any(haystack, ("phong ban chuc nang", "phong dao tao", "lien he")):
        return "department"
    if contains_any(url_title, ("khoa-truc-thuoc", "khoa truc thuoc")) or "khoa truc thuoc" in haystack:
        return "department"
    if contains_any(url_title, ("dang-doan-the", "doan the")) or contains_any(haystack, ("dang bo", "doan thanh nien", "cong doan")):
        return "organization"
    if contains_any(url_title, ("su-menh-tam-nhin", "chien-luoc-phat-trien", "gioi-thieu")) or contains_any(haystack, ("su mang", "tam nhin", "chien luoc phat trien")):
        return "general_info"
    if contains_any(url_title, ("bac-dai-hoc", "toan-co-tin-hoc")) or contains_any(haystack, ("thac si", "tien si", "toan ung dung", "tin hoc")):
        return "program"
    if "lich-su-phat-trien" in url_title:
        return "general_info"
    if contains_any(haystack, ("thong bao", "thong-tin-moi", "tin tuc")):
        return "announcement"
    if contains_any(haystack, ("tuyen sinh", "xet tuyen")):
        return "admission"
    if contains_any(haystack, ("chuong trinh dao tao", "khung chuong trinh", "hoc phan")):
        return "curriculum"
    if contains_any(haystack, ("nganh hoc", "nganh dao tao", "ma nganh", "to hop xet tuyen")):
        return "program"
    if contains_any(haystack, ("quy che", "quy dinh", "quyet dinh")):
        return "regulation"
    return "unknown"


def contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)

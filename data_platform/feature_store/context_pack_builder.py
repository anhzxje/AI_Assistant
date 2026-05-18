"""Build compact topic context packs for LLM prompting and admin review."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from data_platform.processing.cleaners.text_cleaner import normalize_for_match


TOPIC_DEFINITIONS: dict[str, dict[str, object]] = {
    "admissions": {
        "document_types": {"admission"},
        "keywords": {"tuyen sinh", "xet tuyen", "nhap hoc", "hoc phi", "hoc bong"},
    },
    "curriculum": {
        "document_types": {"curriculum", "regulation"},
        "keywords": {"chuong trinh dao tao", "khung chuong trinh", "tin chi", "mon hoc", "khoa hoc du lieu"},
    },
    "lecturers": {
        "document_types": {"lecturer_profile"},
        "keywords": {"giang vien", "can bo", "giao su", "pho giao su", "danh sach can bo"},
    },
    "leadership": {
        "document_types": {"leadership"},
        "keywords": {"hieu truong", "pho hieu truong", "ban giam hieu", "lanh dao", "hoi dong truong"},
    },
    "regulations": {
        "document_types": {"regulation"},
        "keywords": {"quy che", "quy dinh", "dao tao", "tot nghiep", "hoc vu"},
    },
    "student_procedures": {
        "document_types": {"admission", "regulation"},
        "keywords": {"sinh vien", "nhap hoc", "ho so", "hoc bong", "thu tuc"},
    },
    "announcements": {
        "document_types": {"announcement"},
        "keywords": {"thong bao", "tin tuc", "su kien", "lich"},
    },
}


@dataclass(frozen=True)
class TrustedFact:
    text: str
    source_url: str
    title: str | None
    document_type: str
    content_quality_score: float
    authority_score: float
    published_date: str | None


@dataclass(frozen=True)
class ContextPack:
    topic: str
    trusted_facts: list[TrustedFact]
    source_citations: list[dict[str, str | None]]
    last_updated: str
    gaps: list[str]


def build_context_packs(chunks_path: Path, output_dir: Path, *, max_facts_per_topic: int = 8) -> list[ContextPack]:
    chunks = _read_jsonl(chunks_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    packs: list[ContextPack] = []

    for topic, definition in TOPIC_DEFINITIONS.items():
        topic_chunks = _select_topic_chunks(chunks, definition)
        topic_chunks.sort(key=_chunk_rank, reverse=True)
        facts = [_to_fact(chunk) for chunk in topic_chunks[:max_facts_per_topic]]
        citations = _dedupe_citations(facts)
        gaps = _topic_gaps(topic, facts)
        pack = ContextPack(
            topic=topic,
            trusted_facts=facts,
            source_citations=citations,
            last_updated=datetime.now(timezone.utc).isoformat(),
            gaps=gaps,
        )
        packs.append(pack)
        _write_pack(pack, output_dir)

    return packs


def _select_topic_chunks(chunks: list[dict], definition: dict[str, object]) -> list[dict]:
    document_types = set(definition["document_types"])  # type: ignore[arg-type]
    keywords = set(definition["keywords"])  # type: ignore[arg-type]
    selected: list[dict] = []
    for chunk in chunks:
        document_type = str(chunk.get("document_type") or "unknown")
        normalized = normalize_for_match(
            " ".join(
                [
                    str(chunk.get("title") or ""),
                    str(chunk.get("text") or ""),
                    " ".join(str(item) for item in chunk.get("features", {}).get("keyword_hints", [])),
                ]
            )
        )
        if document_type in document_types or any(keyword in normalized for keyword in keywords):
            selected.append(chunk)
    return selected


def _chunk_rank(chunk: dict) -> float:
    features = chunk.get("features", {})
    return (
        float(features.get("content_quality_score") or 0.0) * 0.6
        + float(features.get("authority_score") or 0.0) * 0.25
        + float(features.get("freshness_score") or 0.0) * 0.15
        - float(features.get("boilerplate_score") or 0.0) * 0.25
    )


def _to_fact(chunk: dict) -> TrustedFact:
    features = chunk.get("features", {})
    metadata = chunk.get("metadata", {})
    return TrustedFact(
        text=_compact_text(str(chunk.get("text") or "")),
        source_url=str(chunk.get("source_url") or ""),
        title=chunk.get("title"),
        document_type=str(chunk.get("document_type") or "unknown"),
        content_quality_score=round(float(features.get("content_quality_score") or 0.0), 3),
        authority_score=round(float(features.get("authority_score") or 0.0), 3),
        published_date=metadata.get("published_date"),
    )


def _compact_text(text: str, *, max_chars: int = 700) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "…"


def _dedupe_citations(facts: list[TrustedFact]) -> list[dict[str, str | None]]:
    seen: set[str] = set()
    citations: list[dict[str, str | None]] = []
    for fact in facts:
        if fact.source_url in seen:
            continue
        seen.add(fact.source_url)
        citations.append(
            {
                "title": fact.title,
                "source_url": fact.source_url,
                "document_type": fact.document_type,
                "published_date": fact.published_date,
            }
        )
    return citations


def _topic_gaps(topic: str, facts: list[TrustedFact]) -> list[str]:
    if not facts:
        return [f"No high-quality chunks matched topic '{topic}'."]
    gaps: list[str] = []
    if topic == "leadership" and not any("Hiệu trưởng" in fact.text for fact in facts):
        gaps.append("Leadership pack does not include rector information.")
    if len({fact.source_url for fact in facts}) < 2:
        gaps.append("Only one source is represented; admin review should confirm coverage.")
    return gaps


def _write_pack(pack: ContextPack, output_dir: Path) -> None:
    json_path = output_dir / f"{pack.topic}.json"
    markdown_path = output_dir / f"{pack.topic}.md"
    json_path.write_text(json.dumps(asdict(pack), ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_to_markdown(pack), encoding="utf-8")


def _to_markdown(pack: ContextPack) -> str:
    lines = [
        f"# {pack.topic}",
        "",
        f"Last updated: {pack.last_updated}",
        "",
        "## Trusted facts",
    ]
    for index, fact in enumerate(pack.trusted_facts, start=1):
        lines.append(f"{index}. {fact.text}")
        lines.append(f"   Source: {fact.source_url}")
    lines.extend(["", "## Gaps"])
    lines.extend(f"- {gap}" for gap in (pack.gaps or ["No obvious gaps detected."]))
    lines.append("")
    return "\n".join(lines)


def _read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records

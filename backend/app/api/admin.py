"""Read-only admin/BI endpoints backed by local JSON artifacts."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.services.auth.auth_service import require_admin_user
from backend.app.services.llm_service import OllamaService, llm_status
from backend.app.services.retriever_service import clear_retrieval_cache, get_retriever_service, qdrant_status
from data_platform.config import get_settings
from data_platform.feature_store.embeddings.qdrant_client_factory import create_qdrant_client
from data_platform.feedback.feedback_store import FeedbackStore
from data_platform.governance.data_versioning import latest_data_version
from data_platform.governance.lineage import lineage_status
from data_platform.governance.schema_registry import schema_registry_status
from data_platform.jobs.job_store import JobStore
from ai_module.model_registry.registry import load_registry

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin_user)])


@router.post("/llm/warmup")
def warmup_llm() -> dict[str, Any]:
    service = OllamaService()
    ok = service.warmup()
    embedding_ok = True
    embedding_model = None
    try:
        embedding_model = get_retriever_service().embedding_model.info.model_name
    except Exception:
        embedding_ok = False
    return {
        "ok": ok and embedding_ok,
        "llm": "ollama" if ok else "unavailable",
        "model": service.model,
        "embedding_model": embedding_model,
        "embedding_ok": embedding_ok,
        "latency_ms": service.last_latency_ms,
        "error": service.last_error,
    }


@router.post("/cache/clear-retrieval")
def clear_retrieval_cache_endpoint() -> dict[str, Any]:
    return {"deleted": clear_retrieval_cache()}


@router.get("/documents")
def list_documents(
    q: str | None = Query(default=None),
    document_type: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    path = latest_documents_path()
    rows = read_jsonl(path)

    filtered: list[dict[str, Any]] = []
    q_lower = q.lower() if q else None
    domain_lower = normalize_domain(domain) if domain else None
    for row in rows:
        if document_type and row.get("document_type") != document_type:
            continue
        if domain_lower and domain_from_url(row.get("source_url")) != domain_lower:
            continue
        if q_lower:
            haystack = f"{row.get('title') or ''} {row.get('source_url') or ''} {row.get('text') or ''}".lower()
            if q_lower not in haystack:
                continue
        filtered.append(document_summary(row))
        if len(filtered) >= limit:
            break

    return {
        "total": len(rows),
        "count": len(filtered),
        "documents": filtered,
        "source_path": str(path),
    }


@router.get("/feature-summary")
def feature_summary() -> dict[str, Any]:
    path = latest_feature_summary_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    data["source_path"] = str(path)
    return data


@router.get("/qa-reports")
def qa_reports() -> dict[str, Any]:
    root = Path("qa_ba/reports")
    reports: dict[str, Any] = {}
    for name in (
        "data_quality_report.json",
        "retrieval_eval_report.json",
        "rag_eval_report.json",
        "feedback_eval_report.json",
        "drift_report.json",
    ):
        path = root / name
        if path.exists():
            reports[name] = json.loads(path.read_text(encoding="utf-8"))
    return {
        "reports": reports,
        "available_reports": sorted(reports),
    }


@router.get("/data-layer-summary")
def data_layer_summary() -> dict[str, Any]:
    settings = get_settings()
    documents = safe_read_jsonl(latest_documents_path)
    chunks = safe_read_jsonl(latest_chunks_path)
    feature = safe_load_feature_summary()
    qa = load_qa_report_map()
    data_quality = qa.get("data_quality_report.json", {})
    version = latest_data_version()
    schema = schema_registry_status()
    lineage = lineage_status(limit=5)
    raw_counts = count_layer_files(settings.resolved_data_root / "raw")
    processed_counts = count_layer_files(settings.resolved_data_root / "processed")
    feature_counts = count_layer_files(settings.resolved_data_root / "features")
    file_ingestion = build_file_ingestion_summary(settings.resolved_data_root)
    file_quality_issues = int((data_quality.get("file_ingestion") or {}).get("issue_count") or 0)
    docs_quality_issues = int(data_quality.get("processed_documents", {}).get("issue_count") or 0)
    chunk_quality_issues = int(data_quality.get("chunks", {}).get("issue_count") or 0)

    return {
        "layers": {
            "raw": raw_counts,
            "processed": {
                **processed_counts,
                "documents": len(documents),
                "policy": "regenerable cleaned/normalized records",
            },
            "features": {
                **feature_counts,
                "chunks": len(chunks),
                "qdrant_points": qdrant_points_count(feature),
                "policy": "AI-ready chunks, embeddings, scores, and context packs",
            },
        },
        "latest_data_version": version,
        "schema_registry": schema,
        "lineage": lineage,
        "data_quality": {
            "status": "pass" if not docs_quality_issues and not chunk_quality_issues and not file_quality_issues else "review",
            "report": data_quality,
        },
        "file_ingestion": file_ingestion,
        "source_domain_counts": dict(Counter(domain_from_url(doc.get("source_url")) for doc in documents)),
        "document_type_counts": dict(Counter(str(doc.get("document_type") or "unknown") for doc in documents)),
        "governance": {
            "raw_immutable": True,
            "access_control": "admin endpoints require admin role; user data is scoped by authenticated user_id",
            "allowed_domains": list(settings.allowed_domains),
            "dvc_compatible_metadata": True,
            "streaming_mvp": "Redis/cache plus JSONL job queues; see data_platform/ingestion/streaming/README.md",
        },
    }


@router.get("/model-registry")
def model_registry() -> dict[str, Any]:
    return load_registry()


@router.get("/system-summary")
def system_summary() -> dict[str, Any]:
    summary = safe_load_feature_summary()
    qa = load_qa_report_map()
    documents = safe_read_jsonl(latest_documents_path)
    chunks = safe_read_jsonl(latest_chunks_path)
    qdrant_points = qdrant_points_count(summary)
    feedback_summary = FeedbackStore().summary()
    jobs = JobStore().list_jobs(limit=10000)
    job_counts = Counter(job.status for job in jobs)

    source_health = build_source_health(documents, chunks)
    data_quality = qa.get("data_quality_report.json", {})
    processed_quality = data_quality.get("processed_documents", {})
    duplicate_hash_count = int(processed_quality.get("duplicate_content_hash_count") or 0)
    stale_count = int(processed_quality.get("stale_or_unknown_date_count") or 0)
    unknown_chunks = int((summary.get("chunks_by_document_type") or {}).get("unknown") or 0)
    missing_indicators = build_missing_knowledge_indicators(
        summary=summary,
        duplicate_hash_count=duplicate_hash_count,
        stale_count=stale_count,
        qdrant_points=qdrant_points,
    )

    return {
        "health": {
            "status": "ok",
            "qdrant": qdrant_status(),
            "llm": llm_status(),
            "qdrant_points": qdrant_points,
            "collection": get_settings().qdrant_collection,
        },
        "data": {
            "total_documents": int(summary.get("total_documents") or len(documents)),
            "total_chunks": int(summary.get("total_chunks") or len(chunks)),
            "qdrant_points": qdrant_points,
            "chunks_by_document_type": summary.get("chunks_by_document_type") or {},
            "top_domains": top_domains(summary, source_health),
            "average_chunk_length": float(summary.get("average_chunk_length") or average_chunk_length(chunks)),
            "empty_or_skipped_count": int(summary.get("empty_or_skipped_count") or 0),
            "duplicate_content_hash_count": duplicate_hash_count,
            "stale_or_unknown_date_count": stale_count,
            "unknown_chunk_count": unknown_chunks,
            "source_health": source_health,
            "missing_knowledge_indicators": missing_indicators,
        },
        "qa": {
            "data_quality": data_quality,
            "retrieval_eval": qa.get("retrieval_eval_report.json", {}),
            "rag_eval": qa.get("rag_eval_report.json", {}),
            "feedback_eval": qa.get("feedback_eval_report.json", {}),
        },
        "feedback": feedback_summary,
        "jobs": {
            "pending": job_counts.get("pending", 0),
            "running": job_counts.get("running", 0),
            "success": job_counts.get("success", 0),
            "failed": job_counts.get("failed", 0),
            "skipped": job_counts.get("skipped", 0),
        },
    }


@router.get("/document/{document_id}")
def document_detail(document_id: str) -> dict[str, Any]:
    documents_path = latest_documents_path()
    chunks_path = latest_chunks_path()
    documents = read_jsonl(documents_path)
    document = next((row for row in documents if row.get("document_id") == document_id), None)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = [chunk_summary(row) for row in read_jsonl(chunks_path) if row.get("document_id") == document_id]
    detail = document_summary(document)
    detail.update(
        {
            "text": document.get("text") or "",
            "text_preview": preview_text(document.get("text"), limit=1200),
            "headings": document.get("headings") or [],
            "links": document.get("links") or [],
            "tables": document.get("tables") or [],
            "metadata": document.get("metadata") or {},
        }
    )
    return {
        "document": detail,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "source_path": str(documents_path),
        "chunks_path": str(chunks_path),
    }


@router.get("/chunks")
def list_chunks(
    document_type: str | None = Query(default=None),
    source_url: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    path = latest_chunks_path()
    rows = read_jsonl(path)
    source_lower = source_url.lower() if source_url else None
    domain_lower = normalize_domain(domain) if domain else None
    keyword_lower = keyword.lower() if keyword else None

    filtered: list[dict[str, Any]] = []
    for row in rows:
        row_source = str(row.get("source_url") or "")
        if document_type and row.get("document_type") != document_type:
            continue
        if source_lower and source_lower not in row_source.lower():
            continue
        if domain_lower and domain_from_url(row_source) != domain_lower:
            continue
        if keyword_lower:
            haystack = " ".join(
                [
                    str(row.get("title") or ""),
                    row_source,
                    str(row.get("text") or ""),
                    json.dumps(row.get("keyword_hints") or [], ensure_ascii=False),
                ]
            ).lower()
            if keyword_lower not in haystack:
                continue
        filtered.append(chunk_summary(row))
        if len(filtered) >= limit:
            break

    return {
        "total": len(rows),
        "count": len(filtered),
        "chunks": filtered,
        "source_path": str(path),
    }


def latest_file(root: Path, filename: str) -> Path:
    candidates = sorted(root.glob(f"*/{filename}"))
    if not candidates:
        raise FileNotFoundError(f"No {filename} found under {root}")
    return candidates[-1]


def latest_documents_path() -> Path:
    return latest_file(get_settings().resolved_data_root / "processed" / "documents", "processed_documents.jsonl")


def latest_chunks_path() -> Path:
    return latest_file(get_settings().resolved_data_root / "features" / "chunks", "document_chunks.jsonl")


def latest_feature_summary_path() -> Path:
    return latest_file(get_settings().resolved_data_root / "features" / "metadata", "feature_summary.json")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def safe_read_jsonl(path_getter: Any) -> list[dict[str, Any]]:
    try:
        return read_jsonl(path_getter())
    except Exception:
        return []


def safe_load_feature_summary() -> dict[str, Any]:
    try:
        return feature_summary()
    except Exception:
        return {}


def load_qa_report_map() -> dict[str, Any]:
    return qa_reports()["reports"]


def count_layer_files(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"path": str(root), "file_count": 0, "bytes": 0, "policy": "not initialized"}
    files = [path for path in root.rglob("*") if path.is_file()]
    by_extension = Counter(path.suffix.lower() or "<none>" for path in files)
    return {
        "path": str(root),
        "file_count": len(files),
        "bytes": sum(path.stat().st_size for path in files),
        "by_extension": dict(by_extension),
        "policy": "append-only snapshots" if root.name == "raw" else "regenerable derived artifacts",
    }


def build_file_ingestion_summary(data_root: Path) -> dict[str, Any]:
    manifest_path = data_root / "metadata" / "file_ingestion_manifest.jsonl"
    records = read_jsonl(manifest_path) if manifest_path.exists() else []
    latest = latest_manifest_success_by_source(records)
    summary = {
        "csv": {"count": 0, "rows": 0, "status": "missing"},
        "json": {"count": 0, "rows": 0, "status": "missing"},
        "excel": {"count": 0, "rows": 0, "status": "missing"},
    }
    for record in latest:
        file_type = str(record.get("file_type") or "")
        if file_type not in summary:
            continue
        summary[file_type]["count"] += 1
        summary[file_type]["rows"] += int(record.get("row_count") or 0)
        summary[file_type]["status"] = "ok"
    latest_ingested_at = max((str(record.get("ingested_at") or "") for record in latest), default=None)
    return {
        **summary,
        "latest_manifest": str(manifest_path) if manifest_path.exists() else None,
        "latest_ingested_at": latest_ingested_at,
        "record_count": len(records),
    }


def latest_manifest_success_by_source(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_source: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.get("status") != "success":
            continue
        source = str(record.get("source_path") or "")
        previous = by_source.get(source)
        if previous is None or str(record.get("ingested_at") or "") >= str(previous.get("ingested_at") or ""):
            by_source[source] = record
    return list(by_source.values())


def read_report(name: str) -> dict[str, Any]:
    path = Path("qa_ba/reports") / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def document_summary(row: dict[str, Any]) -> dict[str, Any]:
    source_url = row.get("source_url") or ""
    return {
        "document_id": row.get("document_id"),
        "title": row.get("title"),
        "document_type": row.get("document_type"),
        "source_url": source_url,
        "domain": domain_from_url(source_url),
        "source_path": row.get("source_path"),
        "text_length": len(str(row.get("text") or "")),
        "content_hash": row.get("content_hash"),
        "published_date": row.get("published_date"),
        "language": row.get("language"),
    }


def chunk_summary(row: dict[str, Any]) -> dict[str, Any]:
    text = str(row.get("text") or "")
    source_url = row.get("source_url") or ""
    features = row.get("features") or {}
    return {
        "chunk_id": row.get("chunk_id"),
        "document_id": row.get("document_id"),
        "title": row.get("title"),
        "document_type": row.get("document_type"),
        "source_url": source_url,
        "domain": domain_from_url(source_url),
        "source_path": row.get("source_path"),
        "chunk_index": row.get("chunk_index"),
        "text": text,
        "preview": row.get("preview_text") or (features.get("preview_text") if isinstance(features, dict) else None) or preview_text(text),
        "chunk_text_full": row.get("chunk_text_full") or text,
        "preview_text": row.get("preview_text") or (features.get("preview_text") if isinstance(features, dict) else None),
        "section_heading": row.get("section_heading") or features.get("section_heading"),
        "context_before": row.get("context_before") or (row.get("metadata") or {}).get("context_before"),
        "context_after": row.get("context_after") or (row.get("metadata") or {}).get("context_after"),
        "text_length": len(text),
        "character_start": row.get("character_start"),
        "character_end": row.get("character_end"),
        "content_hash": row.get("content_hash"),
        "keyword_hints": row.get("keyword_hints") or [],
        "features": features,
        "metadata": row.get("metadata") or {},
        "freshness_score": features.get("freshness_score"),
        "authority_score": features.get("authority_score"),
        "boilerplate_score": features.get("boilerplate_score"),
        "menu_density_score": features.get("menu_density_score"),
        "content_quality_score": features.get("content_quality_score"),
    }


def preview_text(value: Any, *, limit: int = 260) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    boundary = text.rfind(" ", int(limit * 0.65), limit)
    end = boundary if boundary > 0 else limit
    return f"{text[:end].rstrip(' ,;:')}…"


def domain_from_url(value: Any) -> str:
    url = str(value or "")
    if not url:
        return "unknown"
    parsed = urlparse(url)
    host = parsed.hostname or parsed.path.split("/")[0]
    return normalize_domain(host or "unknown")


def normalize_domain(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text[4:] if text.startswith("www.") else text


def top_domains(summary: dict[str, Any], source_health: list[dict[str, Any]]) -> list[dict[str, Any]]:
    domains = summary.get("top_domains") or {}
    if isinstance(domains, dict) and domains:
        return [{"domain": key, "count": value} for key, value in domains.items()]
    return [{"domain": item["domain"], "count": item["chunk_count"]} for item in source_health]


def average_chunk_length(chunks: list[dict[str, Any]]) -> float:
    if not chunks:
        return 0.0
    return sum(len(str(chunk.get("text") or "")) for chunk in chunks) / len(chunks)


def qdrant_points_count(summary: dict[str, Any]) -> int:
    settings = get_settings()
    try:
        client = create_qdrant_client(qdrant_url=settings.qdrant_url, local_path=settings.resolved_qdrant_local_path)
        return int(client.count(collection_name=settings.qdrant_collection, exact=True).count)
    except Exception:
        return int(summary.get("total_chunks") or 0)


def build_source_health(documents: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    doc_domains: dict[str, list[dict[str, Any]]] = defaultdict(list)
    chunk_domains: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        doc_domains[domain_from_url(document.get("source_url"))].append(document)
    for chunk in chunks:
        chunk_domains[domain_from_url(chunk.get("source_url"))].append(chunk)

    results: list[dict[str, Any]] = []
    for domain in sorted(set(doc_domains) | set(chunk_domains)):
        domain_docs = doc_domains.get(domain, [])
        domain_chunks = chunk_domains.get(domain, [])
        type_counts = Counter(str(doc.get("document_type") or "unknown") for doc in domain_docs)
        stale_docs = sum(1 for doc in domain_docs if is_stale_or_unknown(doc.get("published_date")))
        duplicate_hashes = duplicate_hash_count(domain_docs)
        freshness_values = [
            float((chunk.get("features") or {}).get("freshness_score"))
            for chunk in domain_chunks
            if isinstance((chunk.get("features") or {}).get("freshness_score"), (int, float))
        ]
        authority_values = [
            float((chunk.get("features") or {}).get("authority_score"))
            for chunk in domain_chunks
            if isinstance((chunk.get("features") or {}).get("authority_score"), (int, float))
        ]
        status = "healthy"
        if duplicate_hashes or stale_docs:
            status = "review"
        if not domain_chunks:
            status = "missing_features"
        results.append(
            {
                "domain": domain,
                "document_count": len(domain_docs),
                "chunk_count": len(domain_chunks),
                "document_types": dict(type_counts),
                "stale_or_unknown_documents": stale_docs,
                "duplicate_content_hashes": duplicate_hashes,
                "average_freshness_score": average(freshness_values),
                "average_authority_score": average(authority_values),
                "status": status,
            }
        )
    results.sort(key=lambda item: item["chunk_count"], reverse=True)
    return results


def duplicate_hash_count(documents: list[dict[str, Any]]) -> int:
    counts = Counter(doc.get("content_hash") for doc in documents if doc.get("content_hash"))
    return sum(1 for count in counts.values() if count > 1)


def is_stale_or_unknown(value: Any) -> bool:
    if not value:
        return True
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return True
    now = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (now - parsed).days > 365


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def build_missing_knowledge_indicators(
    *,
    summary: dict[str, Any],
    duplicate_hash_count: int,
    stale_count: int,
    qdrant_points: int,
) -> list[dict[str, Any]]:
    indicators: list[dict[str, Any]] = []
    unknown_chunks = int((summary.get("chunks_by_document_type") or {}).get("unknown") or 0)
    total_chunks = int(summary.get("total_chunks") or 0)
    empty_or_skipped = int(summary.get("empty_or_skipped_count") or 0)
    if unknown_chunks:
        indicators.append(
            {
                "label": "Unknown document type chunks",
                "count": unknown_chunks,
                "severity": "medium",
                "action": "Review classification rules for uncategorized sources.",
            }
        )
    if stale_count:
        indicators.append(
            {
                "label": "Stale or undated documents",
                "count": stale_count,
                "severity": "high",
                "action": "Queue targeted recrawl for sources with missing or old dates.",
            }
        )
    if duplicate_hash_count:
        indicators.append(
            {
                "label": "Duplicate document hashes",
                "count": duplicate_hash_count,
                "severity": "medium",
                "action": "Review duplicate source handling before the next reindex.",
            }
        )
    if empty_or_skipped:
        indicators.append(
            {
                "label": "Empty or skipped documents",
                "count": empty_or_skipped,
                "severity": "medium",
                "action": "Inspect parser output and source availability.",
            }
        )
    if total_chunks and qdrant_points != total_chunks:
        indicators.append(
            {
                "label": "Qdrant point count mismatch",
                "count": abs(qdrant_points - total_chunks),
                "severity": "high",
                "action": "Queue a reindex to align vector storage with latest chunks.",
            }
        )
    if not indicators:
        indicators.append(
            {
                "label": "No urgent missing knowledge signal",
                "count": 0,
                "severity": "low",
                "action": "Continue monitoring feedback and QA reports.",
            }
        )
    return indicators

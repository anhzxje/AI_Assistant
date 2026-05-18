"""Pydantic schemas for RAG API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    use_llm: bool = True
    user_id: str = "default"
    session_id: str | None = None
    include_memory: bool = True


class Citation(BaseModel):
    title: str | None
    source_url: str
    document_type: str
    chunk_id: str | None
    score: float
    preview: str
    snippet: str | None = None
    full_text: str | None = None
    chunk_text_full: str | None = None
    preview_text: str | None = None
    section_heading: str | None = None
    context_before: str | None = None
    context_after: str | None = None
    usage: str = "cited"
    citation_index: int | None = None
    relevance_reason: str = ""
    used_in_answer: bool = True


class RetrievalMetadata(BaseModel):
    top_k: int
    collection: str
    embedding_model: str


class RagResponseMetadata(BaseModel):
    latency_ms: int
    mode: str
    memory_items: int = 0
    retrieval_confidence: str = "unknown"
    best_score: float | None = None
    debug_retrieval_count: int = 0
    cache_hit: bool = False
    query_type: str = "general"
    embedding_latency_ms: int | None = None
    retrieval_latency_ms: int | None = None
    reranking_latency_ms: int | None = None
    llm_generation_latency_ms: int | None = None
    answer_synthesis_latency_ms: int | None = None
    citation_formatting_latency_ms: int | None = None
    llm_error: str | None = None
    fast_path: dict[str, Any] = Field(default_factory=dict)


class RagQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    debug_retrieval: list[Citation] = Field(default_factory=list)
    retrieval: RetrievalMetadata
    metadata: RagResponseMetadata

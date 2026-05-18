"""Schemas for the local personal knowledge graph foundation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeNode(BaseModel):
    node_id: str
    node_type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class KnowledgeEdge(BaseModel):
    edge_id: str
    source_id: str
    target_id: str
    edge_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):
    user_id: str
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

"""Knowledge foundation APIs."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, Query

from backend.app.services.auth.auth_service import get_current_user
from backend.app.services.auth.user_store import UserRecord
from backend.app.services.knowledge.knowledge_store import KnowledgeStore

router = APIRouter(tags=["knowledge"])


@router.get("/api/knowledge/summary")
def knowledge_summary(user: UserRecord = Depends(get_current_user)) -> dict[str, Any]:
    return get_knowledge_store().summary(user_id=user.user_id)


@router.get("/api/knowledge/graph")
def knowledge_graph(
    node_type: str | None = Query(default=None),
    edge_type: str | None = Query(default=None),
    query: str | None = Query(default=None),
    limit: int = Query(default=250, ge=1, le=1000),
    user: UserRecord = Depends(get_current_user),
) -> dict[str, Any]:
    graph = get_knowledge_store().graph(user_id=user.user_id)
    nodes = graph.nodes
    edges = graph.edges

    if node_type:
        wanted_node_types = normalize_csv_filter(node_type)
        nodes = [node for node in nodes if node.node_type.lower() in wanted_node_types]

    if query:
        lowered_query = query.strip().lower()
        if lowered_query:
            nodes = [
                node
                for node in nodes
                if lowered_query in node.node_id.lower()
                or lowered_query in node.label.lower()
                or lowered_query in stringify_metadata(node.properties).lower()
            ]

    node_ids = {node.node_id for node in nodes}
    edges = [edge for edge in edges if edge.source_id in node_ids and edge.target_id in node_ids]

    if edge_type:
        wanted_edge_types = normalize_csv_filter(edge_type)
        edges = [edge for edge in edges if edge.edge_type.lower() in wanted_edge_types]
        connected_ids = {edge.source_id for edge in edges} | {edge.target_id for edge in edges}
        nodes = [node for node in nodes if node.node_id in connected_ids]
        node_ids = {node.node_id for node in nodes}

    if len(nodes) > limit:
        kept_ids = {node.node_id for node in nodes[:limit]}
        nodes = nodes[:limit]
        edges = [edge for edge in edges if edge.source_id in kept_ids and edge.target_id in kept_ids]
        node_ids = kept_ids

    degree = Counter[str]()
    for edge in edges:
        degree[edge.source_id] += 1
        degree[edge.target_id] += 1

    normalized_nodes = [
        {
            "id": node.node_id,
            "type": node.node_type,
            "label": node.label,
            "metadata": node.properties,
            "source_count": degree[node.node_id],
            # Backward-compatible aliases for existing local consumers.
            "node_id": node.node_id,
            "node_type": node.node_type,
            "properties": node.properties,
        }
        for node in nodes
    ]
    normalized_edges = [
        {
            "id": edge.edge_id,
            "source": edge.source_id,
            "target": edge.target_id,
            "type": edge.edge_type,
            "weight": edge.properties.get("weight", 1) if isinstance(edge.properties, dict) else 1,
            "metadata": edge.properties,
            # Backward-compatible aliases for existing local consumers.
            "edge_id": edge.edge_id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "edge_type": edge.edge_type,
            "properties": edge.properties,
        }
        for edge in edges
        if edge.source_id in node_ids and edge.target_id in node_ids
    ]

    return {
        "user_id": user.user_id,
        "nodes": normalized_nodes,
        "edges": normalized_edges,
        "summary": {
            "node_count": len(normalized_nodes),
            "edge_count": len(normalized_edges),
            "node_counts": dict(Counter(node["type"] for node in normalized_nodes)),
            "edge_counts": dict(Counter(edge["type"] for edge in normalized_edges)),
            "filters": {
                "node_type": node_type,
                "edge_type": edge_type,
                "query": query,
                "limit": limit,
            },
        },
        "metadata": graph.metadata,
    }


@lru_cache(maxsize=1)
def get_knowledge_store() -> KnowledgeStore:
    return KnowledgeStore()


def normalize_csv_filter(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def stringify_metadata(value: Any) -> str:
    try:
        return str(value)
    except Exception:
        return ""

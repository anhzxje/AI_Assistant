"""JSON-backed local knowledge graph store."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.config import get_backend_settings
from backend.app.services.context.context_engine import ContextEngine

from .knowledge_schema import KnowledgeEdge, KnowledgeGraph, KnowledgeNode
from .relationship_extractor import build_nodes_and_edges


class KnowledgeStore:
    def __init__(self) -> None:
        self.data_root = get_backend_settings().data_settings.resolved_data_root
        self.context_engine = ContextEngine()

    def build_from_context(self, *, user_id: str) -> KnowledgeGraph:
        context = self.context_engine.latest(user_id=user_id) or self.context_engine.build(user_id=user_id)
        nodes, edges = build_nodes_and_edges(context)
        graph = KnowledgeGraph(
            user_id=user_id,
            nodes=nodes,
            edges=edges,
            metadata={"generated_at": datetime.now(timezone.utc).isoformat(), "context_generated_at": context.generated_at},
        )
        self.save(graph)
        return graph

    def graph(self, *, user_id: str) -> KnowledgeGraph:
        return self.build_from_context(user_id=user_id)

    def saved_graph(self, *, user_id: str) -> KnowledgeGraph:
        nodes_path = self._folder(user_id) / "nodes.jsonl"
        edges_path = self._folder(user_id) / "edges.jsonl"
        if not nodes_path.exists() or not edges_path.exists():
            return self.build_from_context(user_id=user_id)
        nodes = [KnowledgeNode.model_validate(item) for item in read_jsonl(nodes_path)]
        edges = [KnowledgeEdge.model_validate(item) for item in read_jsonl(edges_path)]
        return KnowledgeGraph(user_id=user_id, nodes=nodes, edges=edges, metadata={"loaded_at": datetime.now(timezone.utc).isoformat()})

    def summary(self, *, user_id: str) -> dict[str, Any]:
        graph = self.graph(user_id=user_id)
        node_counts = Counter(node.node_type for node in graph.nodes)
        edge_counts = Counter(edge.edge_type for edge in graph.edges)
        top_people = [node.model_dump(mode="json") for node in graph.nodes if node.node_type == "Person"][:10]
        top_projects = [node.model_dump(mode="json") for node in graph.nodes if node.node_type == "Project"][:10]
        recent_deadlines = [node.model_dump(mode="json") for node in graph.nodes if node.node_type == "Deadline"][:10]
        return {
            "user_id": user_id,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "node_counts": dict(node_counts),
            "edge_counts": dict(edge_counts),
            "top_people": top_people,
            "top_projects": top_projects,
            "recent_deadlines": recent_deadlines,
            "metadata": graph.metadata,
        }

    def save(self, graph: KnowledgeGraph) -> None:
        folder = self._folder(graph.user_id)
        folder.mkdir(parents=True, exist_ok=True)
        write_jsonl(folder / "nodes.jsonl", [node.model_dump(mode="json") for node in graph.nodes])
        write_jsonl(folder / "edges.jsonl", [edge.model_dump(mode="json") for edge in graph.edges])

    def _folder(self, user_id: str) -> Path:
        return self.data_root / "features" / "personal" / "knowledge" / user_id


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

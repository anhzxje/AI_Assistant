"""Extract graph relationships from personal context."""

from __future__ import annotations

from typing import Any

from backend.app.services.context.context_schema import PersonalContext

from .knowledge_schema import KnowledgeEdge, KnowledgeNode


def build_nodes_and_edges(context: PersonalContext) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
    nodes: dict[str, KnowledgeNode] = {}
    edges: dict[str, KnowledgeEdge] = {}

    def add_node(node_type: str, key: str, label: str, **properties: Any) -> str:
        node_id = f"{node_type}:{key}"
        nodes[node_id] = KnowledgeNode(node_id=node_id, node_type=node_type, label=label, properties=properties)
        return node_id

    def add_edge(source_id: str, target_id: str, edge_type: str, **properties: Any) -> None:
        edge_id = f"{source_id}->{edge_type}->{target_id}"
        edges[edge_id] = KnowledgeEdge(edge_id=edge_id, source_id=source_id, target_id=target_id, edge_type=edge_type, properties=properties)

    for person in context.people:
        email = str(person.get("email") or person.get("name") or "").lower()
        if email:
            add_node("Person", email, str(person.get("name") or email), email=email, mention_count=person.get("mention_count", 0))

    for project in context.projects:
        project_id = add_node("Project", project.project_id, project.name, keywords=project.keywords, score=project.score)
        for source_id in project.source_ids:
            source_node = source_id_to_node(context, source_id)
            if source_node:
                add_edge(project_id, source_node.node_id, "RELATED_TO")
                nodes[source_node.node_id] = source_node

    for task in context.tasks:
        task_id = add_node("Task", task.task_id, task.title, due_date=task.due_date, priority=task.priority, score=task.score)
        source_node = source_id_to_node(context, task.source_id)
        if source_node:
            nodes[source_node.node_id] = source_node
            add_edge(task_id, source_node.node_id, "RELATED_TO", source_type=task.source_type)

    for deadline in context.deadlines:
        deadline_id = add_node("Deadline", str(deadline.get("deadline_id")), str(deadline.get("title") or "Deadline"), date_text=deadline.get("date_text"))
        source_node = source_id_to_node(context, str(deadline.get("source_id")))
        if source_node:
            nodes[source_node.node_id] = source_node
            add_edge(deadline_id, source_node.node_id, "DEADLINE_FOR")

    for item in context.source_items:
        node_type = "EmailThread" if item.source_type == "gmail" else "CalendarEvent"
        source_node_id = add_node(node_type, item.source_id, item.title, source_type=item.source_type, **item.metadata)
        if item.source_type == "gmail":
            sender = str(item.metadata.get("from") or "")
            sender_email = sender_email_from_header(sender)
            if sender_email:
                person_id = add_node("Person", sender_email, sender_email, email=sender_email)
                add_edge(person_id, source_node_id, "SENT")
        if item.url:
            doc_id = add_node("Document", item.url, item.title, url=item.url)
            add_edge(source_node_id, doc_id, "HAS_ATTACHMENT" if item.metadata.get("has_attachment") else "RELATED_TO")

    for organization in context.metadata.get("organizations", []):
        add_node("Organization", str(organization).lower(), str(organization))
    for course in context.metadata.get("courses", []):
        add_node("Course", str(course).lower(), str(course))

    return list(nodes.values()), list(edges.values())


def source_id_to_node(context: PersonalContext, source_id: str) -> KnowledgeNode | None:
    for item in context.source_items:
        if item.source_id == source_id:
            node_type = "EmailThread" if item.source_type == "gmail" else "CalendarEvent"
            return KnowledgeNode(node_id=f"{node_type}:{item.source_id}", node_type=node_type, label=item.title, properties=item.metadata)
    return None


def sender_email_from_header(value: str) -> str:
    import re

    match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", value)
    return match.group(0).lower() if match else ""

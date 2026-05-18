from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from qa_ba.api_tests.auth_helpers import user_headers


client = TestClient(app)


def login_headers(email: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def current_user_id(headers: dict[str, str]) -> str:
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    return response.json()["user"]["user_id"]


def prepare_graph(headers: dict[str, str]) -> dict:
    user_id = current_user_id(headers)
    sync = client.post(
        "/api/google/gmail/sync",
        headers=headers,
        json={"user_id": user_id, "use_mock": True, "scenario": "student_deadline_heavy", "max_results": 20},
    )
    assert sync.status_code == 200
    context = client.post("/api/context/generate", headers=headers)
    assert context.status_code == 200
    graph = client.get("/api/knowledge/graph", headers=headers)
    assert graph.status_code == 200
    return graph.json()


def test_knowledge_summary_works() -> None:
    response = client.get("/api/knowledge/summary", headers=user_headers(client))

    assert response.status_code == 200
    body = response.json()
    assert "node_count" in body
    assert "edge_count" in body
    assert isinstance(body["node_counts"], dict)


def test_knowledge_graph_works() -> None:
    response = client.get("/api/knowledge/graph", headers=user_headers(client))

    assert response.status_code == 200
    body = response.json()
    assert "nodes" in body
    assert "edges" in body
    assert "summary" in body
    assert isinstance(body["nodes"], list)
    assert isinstance(body["edges"], list)


def test_knowledge_graph_has_nodes_after_context_generation() -> None:
    body = prepare_graph(user_headers(client))

    assert body["summary"]["node_count"] > 0
    assert body["summary"]["edge_count"] > 0
    first_node = body["nodes"][0]
    assert {"id", "type", "label", "metadata", "source_count"}.issubset(first_node)
    first_edge = body["edges"][0]
    assert {"id", "source", "target", "type", "weight", "metadata"}.issubset(first_edge)


def test_knowledge_graph_filters_do_not_crash() -> None:
    headers = user_headers(client)
    prepare_graph(headers)

    for params in (
        {"node_type": "Person"},
        {"edge_type": "RELATED_TO"},
        {"query": "deadline"},
        {"limit": "5"},
        {"node_type": "EmailThread,Deadline", "edge_type": "DEADLINE_FOR", "query": "h"},
    ):
        response = client.get("/api/knowledge/graph", headers=headers, params=params)
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["nodes"], list)
        assert isinstance(body["edges"], list)
        assert body["summary"]["filters"]


def test_knowledge_graph_is_scoped_to_authenticated_user() -> None:
    user_one_headers = user_headers(client)
    user_one_graph = prepare_graph(user_one_headers)
    user_one_id = current_user_id(user_one_headers)

    user_two_headers = login_headers("user2@omni.local", "user2123456")
    user_two_id = current_user_id(user_two_headers)
    user_two_graph = client.get("/api/knowledge/graph", headers=user_two_headers)

    assert user_two_graph.status_code == 200
    assert user_one_id != user_two_id
    assert user_one_graph["user_id"] == user_one_id
    assert user_two_graph.json()["user_id"] == user_two_id
    assert user_two_graph.json()["user_id"] != user_one_graph["user_id"]

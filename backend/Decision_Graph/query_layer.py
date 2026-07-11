"""
Query layer — what other components (an agent, a frontend viz) call against the
built graph. Kept as plain functions here; wrap in FastAPI (see api.py) once stable.
"""

from collections import Counter, deque
from datetime import datetime

from backend.llm import embed_text
from backend import storage
from backend.logging_config import get_logger

logger = get_logger(__name__)
logger.info(
    "Query layer loaded graph: %d nodes, %d edges",
    storage.G.number_of_nodes(),
    storage.G.number_of_edges(),
)


def find_similar_past_decisions(query_text: str, k: int = 5):
    embedding = embed_text(query_text)
    return storage.query_similar_chunks(embedding, k=k)


def find_similar_past_decisions_clean(query_text: str, k: int = 5) -> dict:
    """Same lookup as find_similar_past_decisions, reshaped into a flat
    {items: [...]} list for API/frontend consumption instead of Chroma's raw
    parallel-arrays shape."""
    raw = find_similar_past_decisions(query_text, k=k)
    ids = raw.get("ids", [[]])[0]
    docs = raw.get("documents", [[]])[0]
    distances = raw.get("distances", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]

    items = []
    for chunk_id, doc, distance, metadata in zip(ids, docs, distances, metadatas):
        metadata = metadata or {}
        items.append(
            {
                "chunk_id": chunk_id,
                "snippet": (doc or "")[:280],
                "distance": float(distance),
                "source_type": metadata.get("source_type"),
                "source_name": metadata.get("source_name") or metadata.get("project") or metadata.get("source_id"),
                "source_url": metadata.get("source_url"),
                "author": metadata.get("author"),
                "timestamp": metadata.get("timestamp"),
                "project": metadata.get("project"),
                "external_id": metadata.get("external_id"),
                "connector_provider": metadata.get("connector_provider"),
                "content_hash": metadata.get("content_hash"),
            }
        )
    return {"items": items}


def why_did_x_fail(node_label: str):
    """Find a node by label and walk its incoming causal edges (what caused it)."""
    matches = [n for n, d in storage.G.nodes(data=True) if d.get("label") == node_label]
    if not matches:
        return None
    node_id = matches[0]
    causes = [
        {"cause_node_id": u, "cause_node": storage.G.nodes[u], "edge": data}
        for u, v, data in storage.G.in_edges(node_id, data=True)
        if data.get("edge_type") == "causal"
    ]
    return {"node_id": node_id, "node": storage.G.nodes[node_id], "causes": causes}


def what_did_x_lead_to(node_label: str):
    """Inverse of why_did_x_fail — outgoing causal edges."""
    matches = [n for n, d in storage.G.nodes(data=True) if d.get("label") == node_label]
    if not matches:
        return None
    node_id = matches[0]
    effects = [
        {"effect_node_id": v, "effect_node": storage.G.nodes[v], "edge": data}
        for u, v, data in storage.G.out_edges(node_id, data=True)
        if data.get("edge_type") == "causal"
    ]
    return {"node_id": node_id, "node": storage.G.nodes[node_id], "effects": effects}


def get_full_graph():
    """Return the full graph as plain dicts (for a frontend viz / API response)."""
    nodes = [{"id": n, **d} for n, d in storage.G.nodes(data=True)]
    edges = [{"source": u, "target": v, **d} for u, v, d in storage.G.edges(data=True)]
    return {"nodes": nodes, "edges": edges}


def _node_type(data: dict) -> str:
    return data.get("node_type") or data.get("type") or "unknown"


def _edge_type(data: dict) -> str:
    return data.get("edge_type") or data.get("type") or "unknown"


def _source_type(data: dict) -> str:
    return data.get("source_type") or data.get("source") or data.get("project") or "unknown"


def _top_nodes(type_name: str, limit: int = 8) -> list[dict]:
    items = []
    for node_id, data in storage.G.nodes(data=True):
        if _node_type(data) != type_name:
            continue
        items.append(
            {
                "id": node_id,
                "label": data.get("label") or node_id,
                "confidence": data.get("confidence", 0),
                "degree": storage.G.degree(node_id),
                "source_type": _source_type(data),
            }
        )
    return sorted(items, key=lambda item: (item["degree"], item["confidence"]), reverse=True)[:limit]


def graph_summary() -> dict:
    """Small, human-readable summary for graph dashboards and default views."""
    node_counts = Counter(_node_type(data) for _, data in storage.G.nodes(data=True))
    edge_counts = Counter(_edge_type(data) for _, _, data in storage.G.edges(data=True))
    projects = Counter(
        data.get("project") or data.get("source_type")
        for _, data in storage.G.nodes(data=True)
        if data.get("project") or data.get("source_type")
    )
    recent = []
    for node_id, data in storage.G.nodes(data=True):
        timestamp = data.get("timestamp") or data.get("created_at") or data.get("updated_at")
        if timestamp:
            recent.append(
                {
                    "id": node_id,
                    "label": data.get("label") or node_id,
                    "timestamp": timestamp,
                    "source_type": _source_type(data),
                }
            )
    recent.sort(key=lambda item: str(item.get("timestamp")), reverse=True)
    degree_items = [
        {
            "id": node_id,
            "label": data.get("label") or node_id,
            "type": _node_type(data),
            "degree": storage.G.degree(node_id),
            "confidence": data.get("confidence", 0),
        }
        for node_id, data in storage.G.nodes(data=True)
    ]
    degree_items.sort(key=lambda item: (item["degree"], item["confidence"]), reverse=True)
    total_nodes = storage.G.number_of_nodes()
    total_edges = storage.G.number_of_edges()
    orphan_nodes = sum(1 for node_id in storage.G.nodes if storage.G.degree(node_id) == 0)
    return {
        "nodeCountsByType": dict(node_counts),
        "edgeCountsByType": dict(edge_counts),
        "topProjects": [{"label": key, "count": value} for key, value in projects.most_common(8)],
        "topDecisions": _top_nodes("decision"),
        "topOutcomes": _top_nodes("outcome"),
        "topPeople": _top_nodes("person"),
        "recentSources": recent[:10],
        "mostConnectedNodes": degree_items[:10],
        "graphHealth": {
            "totalNodes": total_nodes,
            "totalEdges": total_edges,
            "orphanNodes": orphan_nodes,
            "averageDegree": round((2 * total_edges / total_nodes), 2) if total_nodes else 0,
        },
    }


def _serialize_subgraph(node_ids: set[str]) -> dict:
    nodes = [{"id": node_id, **storage.G.nodes[node_id]} for node_id in node_ids if node_id in storage.G]
    edges = [
        {"source": u, "target": v, **data}
        for u, v, data in storage.G.edges(data=True)
        if u in node_ids and v in node_ids
    ]
    return {"nodes": nodes, "edges": edges}


def _important_seed_nodes(limit: int) -> list[str]:
    return [
        node_id
        for node_id, data in sorted(
            storage.G.nodes(data=True),
            key=lambda item: (storage.G.degree(item[0]), item[1].get("confidence", 0)),
            reverse=True,
        )[:limit]
    ]


def focused_graph(query: str | None = None, node_id: str | None = None, depth: int = 1, limit: int = 50) -> dict:
    """Return a bounded graph around a selected/search-matched node set."""
    max_depth = max(0, min(depth, 3))
    max_nodes = max(5, min(limit, 75))
    if node_id and node_id in storage.G:
        seeds = [node_id]
    elif query:
        needle = query.lower().strip()
        matches = []
        for candidate_id, data in storage.G.nodes(data=True):
            haystack = " ".join(
                str(data.get(key, ""))
                for key in ("label", "description", "summaryText", "project", "source_type", "author")
            ).lower()
            if needle and needle in haystack:
                matches.append(candidate_id)
        seeds = matches[:10]
    else:
        seeds = _important_seed_nodes(10)

    selected: set[str] = set()
    queue = deque((seed, 0) for seed in seeds)
    while queue and len(selected) < max_nodes:
        current, level = queue.popleft()
        if current in selected or current not in storage.G:
            continue
        selected.add(current)
        if level >= max_depth:
            continue
        neighbors = set(storage.G.predecessors(current)) | set(storage.G.successors(current))
        ranked = sorted(neighbors, key=lambda neighbor: storage.G.degree(neighbor), reverse=True)
        for neighbor in ranked:
            if len(selected) + len(queue) >= max_nodes:
                break
            queue.append((neighbor, level + 1))

    result = _serialize_subgraph(selected)
    result["metadata"] = {
        "query": query,
        "node_id": node_id,
        "depth": max_depth,
        "limit": max_nodes,
        "totalNodesAvailable": storage.G.number_of_nodes(),
        "focused": storage.G.number_of_nodes() > len(result["nodes"]),
    }
    return result

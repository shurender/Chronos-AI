"""
Query layer — what other components (an agent, a frontend viz) call against the
built graph. Kept as plain functions here; wrap in FastAPI (see api.py) once stable.
"""

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
                "timestamp": metadata.get("timestamp"),
                "project": metadata.get("project"),
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
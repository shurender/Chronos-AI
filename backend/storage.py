"""
Storage: NetworkX (graph structure) + Chroma (vector similarity search over chunks
and, separately, over node descriptions for contradiction detection).
"""

import os
import pickle

import chromadb

from . import config
from .schema import GraphEdge, GraphNode
from .logging_config import get_logger

logger = get_logger(__name__)

# config loads the repo .env consistently, so graph, Chroma, and health checks
# all resolve paths in the same way.
GRAPH_PATH = config.GRAPH_PATH
CHROMA_DB_PATH = config.CHROMA_DB_PATH

import networkx as nx

# --- Graph store ---

G = nx.MultiDiGraph()


def add_node_to_graph(node: GraphNode) -> None:
    G.add_node(node.node_id, **node.model_dump(mode="json"))


def add_edge_to_graph(edge: GraphEdge) -> None:
    G.add_edge(
        edge.source_node_id,
        edge.target_node_id,
        key=edge.edge_id,
        **edge.model_dump(mode="json"),
    )


def save_graph(path: str = GRAPH_PATH):
    logger.info("Saving graph to %s (%d nodes, %d edges)", path, G.number_of_nodes(), G.number_of_edges())

    with open(path, "wb") as f:
        pickle.dump(G, f)


def load_graph(path: str = GRAPH_PATH):
    global G

    exists = os.path.exists(path)
    logger.info("Loading graph from %s (exists=%s)", path, exists)

    if exists:
        with open(path, "rb") as f:
            loaded_graph = pickle.load(f)

        G.clear()

        G.add_nodes_from(loaded_graph.nodes(data=True))

        for u, v, key, data in loaded_graph.edges(keys=True, data=True):
            G.add_edge(u, v, key=key, **data)

    logger.info("Graph ready: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())

    return G


# --- Vector stores (Chroma) ---
# Two collections: one for raw chunks (for similarity search / query layer),
# one for node descriptions (for contradiction detection against the graph).

_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
chunk_collection = _client.get_or_create_collection(name="memory_chunks")
node_collection = _client.get_or_create_collection(name="graph_nodes")


def add_chunk_to_chroma(chunk_id: str, text: str, metadata: dict, embedding: list[float]) -> None:
    # Chroma metadata values must be str/int/float/bool, not None/dict/list.
    clean_meta = _clean_metadata(metadata)
    chunk_collection.upsert(
        ids=[chunk_id], documents=[text], metadatas=[clean_meta], embeddings=[embedding]
    )


def add_node_to_chroma(node: GraphNode, embedding: list[float]) -> None:
    node_collection.upsert(
        ids=[node.node_id],
        documents=[node.description],
        metadatas=[{"label": node.label, "node_type": node.node_type}],
        embeddings=[embedding],
    )


def query_similar_chunks(query_embedding: list[float], k: int = 5):
    return chunk_collection.query(query_embeddings=[query_embedding], n_results=k)


def delete_chunk(chunk_id: str) -> None:
    """Remove one chunk's embedding from the vector store (idempotent)."""
    try:
        chunk_collection.delete(ids=[chunk_id])
    except Exception:  # noqa: BLE001 — deletion is best-effort
        pass


def get_chunk_metadata(chunk_id: str) -> dict | None:
    try:
        result = chunk_collection.get(ids=[chunk_id], include=["metadatas"])
    except Exception:  # noqa: BLE001
        return None
    metadatas = result.get("metadatas") or []
    return metadatas[0] if metadatas else None


def remove_graph_records_for_chunk(chunk_id: str) -> tuple[int, int]:
    """Remove graph nodes/edges derived from a chunk before re-ingesting it."""
    node_ids = [
        node_id
        for node_id, data in G.nodes(data=True)
        if chunk_id in (data.get("source_chunk_ids") or [])
    ]
    edge_keys = [
        (u, v, key)
        for u, v, key, data in G.edges(keys=True, data=True)
        if chunk_id in (data.get("source_chunk_ids") or [])
    ]
    for u, v, key in edge_keys:
        if G.has_edge(u, v, key):
            G.remove_edge(u, v, key)
    for node_id in node_ids:
        if G.has_node(node_id):
            G.remove_node(node_id)
    if node_ids:
        try:
            node_collection.delete(ids=node_ids)
        except Exception:  # noqa: BLE001
            pass
    delete_chunk(chunk_id)
    return len(node_ids), len(edge_keys)


def reset_all() -> None:
    """Clear the in-memory graph, delete the persisted graph file, and empty both
    Chroma collections IN PLACE (not delete+recreate — other modules hold direct
    references to these collection objects via `from backend.storage import
    chunk_collection`, which would go stale if we rebound the name here).
    Used by POST /ingest/reset — destructive, controlled."""
    G.clear()
    if os.path.exists(GRAPH_PATH):
        os.remove(GRAPH_PATH)

    for collection in (chunk_collection, node_collection):
        existing_ids = collection.get()["ids"]
        if existing_ids:
            collection.delete(ids=existing_ids)

    logger.info("Reset complete: graph and Chroma collections cleared")


def query_similar_nodes(query_embedding: list[float], k: int = 5):
    count = node_collection.count()
    if count == 0:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
    return node_collection.query(
        query_embeddings=[query_embedding], n_results=min(k, count)
    )


def _clean_metadata(metadata: dict) -> dict:
    clean = {}
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean

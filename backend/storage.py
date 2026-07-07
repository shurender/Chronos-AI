"""
Storage: NetworkX (graph structure) + Chroma (vector similarity search over chunks
and, separately, over node descriptions for contradiction detection).
"""

import os
import pickle

import chromadb
from dotenv import load_dotenv
from pathlib import Path

from .schema import GraphEdge, GraphNode
BASE_DIR = Path(__file__).resolve().parent

load_dotenv()

GRAPH_PATH = os.getenv("GRAPH_PATH", str(BASE_DIR / "graph.gpickle"))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "chroma_db"))

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
    print("Saving graph to:", path)
    print("Nodes:", G.number_of_nodes())
    print("Edges:", G.number_of_edges())

    with open(path, "wb") as f:
        pickle.dump(G, f)


def load_graph(path: str = GRAPH_PATH):
    global G

    print("GRAPH_PATH =", path)
    print("Exists =", os.path.exists(path))

    if os.path.exists(path):
        with open(path, "rb") as f:
            loaded_graph = pickle.load(f)

        G.clear()

        G.add_nodes_from(loaded_graph.nodes(data=True))

        for u, v, key, data in loaded_graph.edges(keys=True, data=True):
            G.add_edge(u, v, key=key, **data)

    print("Nodes =", G.number_of_nodes())
    print("Edges =", G.number_of_edges())

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
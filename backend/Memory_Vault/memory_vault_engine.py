"""
Memory Vault: turns the extraction graph's `decision` nodes (with their
source_chunk_ids, evidence_type/confidence, and connected outcome/edge data)
into the two shapes /app/memory needs:

  1. A React-Flow-ready graph: N historical decision nodes (chronological)
     -> Current You (root) -> Future Paths (forward node).
  2. A timeline of MemoryEntry objects (year, title, outcome, lesson,
     connects-to tags), each still carrying source_chunk_ids + confidence
     so the UI can cite where it came from.

No LLM calls — pure read/derive over data extraction_pipeline.py already
produced and storage.py persisted (G graph + Chroma chunk_collection for
chunk timestamps).
"""

import datetime as dt
from typing import Optional

from backend.schema import (
    MemoryEntry,
    MemoryVaultGraphEdge,
    MemoryVaultGraphNode,
    MemoryVaultResponse,
)
from backend.storage import G, chunk_collection

CURRENT_YOU_ID = "current_you"
FUTURE_PATHS_ID = "future_paths"
DEFAULT_MAX_DECISIONS = 4


def _chunk_timestamps(chunk_ids: list[str]) -> list[dt.datetime]:
    """Pull timestamps for a decision's source chunks from Chroma metadata."""
    if not chunk_ids:
        return []
    try:
        result = chunk_collection.get(ids=chunk_ids, include=["metadatas"])
    except Exception:
        return []
    out = []
    for meta in result.get("metadatas", []) or []:
        ts = (meta or {}).get("timestamp")
        if not ts:
            continue
        try:
            out.append(dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")))
        except ValueError:
            continue
    return out


def _earliest_year(chunk_ids: list[str], fallback_year: int) -> int:
    timestamps = _chunk_timestamps(chunk_ids)
    return min(timestamps).year if timestamps else fallback_year


def _connected_outcome(decision_node_id: str) -> Optional[tuple[dict, dict]]:
    """Highest-confidence outgoing causal edge from this decision to an
    outcome node, if any: (outcome_node_data, edge_data)."""
    best = None
    for _, v, edge_data in G.out_edges(decision_node_id, data=True):
        if edge_data.get("edge_type") != "causal":
            continue
        target = G.nodes.get(v, {})
        if target.get("node_type") != "outcome":
            continue
        if best is None or edge_data.get("confidence", 0) > best[1].get("confidence", 0):
            best = (target, edge_data)
    return best


def _connects_to_labels(decision_node_id: str) -> list[str]:
    """Skill/project/person nodes touching this decision (either direction)
    -> the 'Connects to' tag chips."""
    labels = set()
    for _, v, _ in G.out_edges(decision_node_id, data=True):
        target = G.nodes.get(v, {})
        if target.get("node_type") in ("skill", "project", "person"):
            labels.add(target.get("label", v))
    for u, _, _ in G.in_edges(decision_node_id, data=True):
        source = G.nodes.get(u, {})
        if source.get("node_type") in ("skill", "project", "person"):
            labels.add(source.get("label", u))
    return sorted(labels)


def _all_decision_nodes() -> list[dict]:
    return [
        {"node_id": n, **data}
        for n, data in G.nodes(data=True)
        if data.get("node_type") == "decision"
    ]


def build_memory_vault(
    current_year: int = 2026,
    max_decisions: int = DEFAULT_MAX_DECISIONS,
) -> MemoryVaultResponse:
    decisions = _all_decision_nodes()

    dated = [
        (d, _earliest_year(d.get("source_chunk_ids", []), current_year))
        for d in decisions
    ]
    dated.sort(key=lambda pair: pair[1])  # oldest -> newest
    if len(dated) > max_decisions:
        dated = dated[-max_decisions:]  # most recent N feed the vault

    memory_entries: list[MemoryEntry] = []
    graph_nodes: list[MemoryVaultGraphNode] = []
    graph_edges: list[MemoryVaultGraphEdge] = []

    previous_node_id = None
    for node, year in dated:
        node_id = node["node_id"]
        outcome_pair = _connected_outcome(node_id)
        outcome_text = (
            outcome_pair[0]["description"] if outcome_pair else "Outcome not yet recorded."
        )
        lesson_text = (
            outcome_pair[1]["description"]
            if outcome_pair
            else "No causal outcome linked yet — lesson pending more chunks."
        )

        source_chunk_ids = list(node.get("source_chunk_ids", []))
        confidence = node.get("confidence", 0.5)
        if outcome_pair:
            source_chunk_ids += [
                c for c in outcome_pair[0].get("source_chunk_ids", []) if c not in source_chunk_ids
            ]
            confidence = min(confidence, outcome_pair[1].get("confidence", confidence))

        memory_entries.append(
            MemoryEntry(
                nodeId=node_id,
                year=year,
                title=node.get("label", "Untitled decision"),
                outcome=outcome_text,
                lesson=lesson_text,
                connectsTo=_connects_to_labels(node_id),
                sourceChunkIds=source_chunk_ids,
                confidence=round(float(confidence), 2),
            )
        )
        graph_nodes.append(
            MemoryVaultGraphNode(id=node_id, nodeType="decision", label=node.get("label", "Untitled decision"), year=year)
        )
        if previous_node_id is not None:
            graph_edges.append(MemoryVaultGraphEdge(source=previous_node_id, target=node_id))
        previous_node_id = node_id

    # earliest entry expands by default (matches "2024 expanded by default" in spec)
    if memory_entries:
        memory_entries[0].expandedByDefault = True

    graph_nodes.append(
        MemoryVaultGraphNode(id=CURRENT_YOU_ID, nodeType="current_you", label=f"Current You · {current_year}", year=current_year)
    )
    if previous_node_id is not None:
        graph_edges.append(MemoryVaultGraphEdge(source=previous_node_id, target=CURRENT_YOU_ID))

    graph_nodes.append(
        MemoryVaultGraphNode(id=FUTURE_PATHS_ID, nodeType="future_paths", label="Future Paths →", year=None)
    )
    graph_edges.append(MemoryVaultGraphEdge(source=CURRENT_YOU_ID, target=FUTURE_PATHS_ID))

    return MemoryVaultResponse(
        graphNodes=graph_nodes,
        graphEdges=graph_edges,
        memoryEntries=memory_entries,
    )
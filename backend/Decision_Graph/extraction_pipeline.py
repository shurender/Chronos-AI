"""
Core build: a small LangGraph StateGraph that turns one chunk into tagged
nodes + edges and writes them into the graph store.

Modeled as discrete steps (not one giant LLM call) so each stage is debuggable
and swappable — e.g. a cheap model for tagging, a stronger one for edge
proposal, all driven from the same Groq client for now.
"""

from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from llm import embed_text, get_chat_model
from schema import (
    CandidateEdges,
    CandidateNodes,
    ContradictionRecord,
    GraphEdge,
    GraphNode,
    Tags,
)
from storage import (
    add_edge_to_graph,
    add_node_to_graph,
    add_node_to_chroma,
    query_similar_nodes,
)

CONTRADICTION_SIMILARITY_THRESHOLD = 0.35  # Chroma L2 distance; lower = more similar


class ExtractionState(TypedDict):
    chunk: dict
    entities: list[dict]  # candidate node dicts: node_type/label/description
    proposed_edges: list[dict]  # candidate edge dicts: source_label/target_label/edge_type/description
    tagged_nodes: list[GraphNode]
    tagged_edges: list[GraphEdge]
    gaps: list[dict]
    contradictions: list[ContradictionRecord]


# --- Node 1: extract entities ---

_ENTITY_SYSTEM_PROMPT = """You are extracting structured entities from a single chunk of \
project history (a commit, Slack message, Notion page, or resume excerpt).

Identify candidate entities of these types only: decision, outcome, person, skill, project.
- decision: a choice that was made (e.g. "switched to Postgres")
- outcome: a result of a decision (e.g. "migration caused two days of downtime")
- person: a named individual or handle involved
- skill: a technology/skill/competency demonstrated or discussed
- project: a named project/repo/initiative

Only extract what the text actually supports. Do not invent facts. Each entity needs a short
label (a few words) and a 1-3 sentence description grounded in the chunk text."""


def extract_entities(state: ExtractionState) -> ExtractionState:
    chunk = state["chunk"]
    llm = get_chat_model().with_structured_output(CandidateNodes)
    result: CandidateNodes = llm.invoke(
        [
            ("system", _ENTITY_SYSTEM_PROMPT),
            ("human", f"Chunk text:\n\n{chunk['raw_text']}"),
        ]
    )
    state["entities"] = [n.model_dump() for n in result.nodes]
    return state


# --- Node 2: propose edges ---

_EDGE_SYSTEM_PROMPT = """Given a list of entities extracted from the same chunk, propose \
edges between them ONLY where the chunk text actually supports a relationship.

Edge types:
- causal: source caused/led to target (e.g. decision -> outcome)
- temporal: source happened before target, no claimed causation
- contributory: source contributed to / was involved in target (e.g. person -> project)

Refer to entities by their exact "label" string. Do not propose edges between entities that
weren't given to you. If there's no clear relationship, return an empty list rather than
guessing."""


def propose_edges(state: ExtractionState) -> ExtractionState:
    entities = state["entities"]
    if len(entities) < 2:
        state["proposed_edges"] = []
        return state

    chunk = state["chunk"]
    llm = get_chat_model().with_structured_output(CandidateEdges)
    entity_listing = "\n".join(f"- ({e['node_type']}) {e['label']}: {e['description']}" for e in entities)
    result: CandidateEdges = llm.invoke(
        [
            ("system", _EDGE_SYSTEM_PROMPT),
            (
                "human",
                f"Chunk text:\n\n{chunk['raw_text']}\n\nEntities:\n{entity_listing}",
            ),
        ]
    )
    state["proposed_edges"] = [e.model_dump() for e in result.edges]
    return state


# --- Node 3: tag fact/inference/prediction + confidence ---

_TAG_SYSTEM_PROMPT = """For each item below (a node or an edge, identified by its label or \
description), classify it as one of:
- fact: directly and explicitly stated in the source text
- inference: reasonably implied but not stated outright
- prediction: a forward-looking claim about something not yet resolved

Also assign a confidence score from 0.0 to 1.0 reflecting how well the source text supports
this item. Be conservative: explicit statements get high confidence (0.8-1.0), reasonable
inferences get medium confidence (0.4-0.7), weak signals get low confidence (0.1-0.3)."""


def tag_fact_inference_prediction(state: ExtractionState) -> ExtractionState:
    chunk = state["chunk"]
    entities = state["entities"]
    edges = state["proposed_edges"]

    if not entities and not edges:
        state["tagged_nodes"] = []
        state["tagged_edges"] = []
        return state

    items_listing = "\n".join(f"- NODE: {e['label']}: {e['description']}" for e in entities)
    items_listing += "\n" + "\n".join(
        f"- EDGE: {e['source_label']} -> {e['target_label']} ({e['edge_type']}): {e['description']}"
        for e in edges
    )

    llm = get_chat_model().with_structured_output(Tags)
    result: Tags = llm.invoke(
        [
            ("system", _TAG_SYSTEM_PROMPT),
            (
                "human",
                f"Source chunk text:\n\n{chunk['raw_text']}\n\nItems to classify:\n{items_listing}",
            ),
        ]
    )

    # Match tags back to items by best-effort substring match on label/description.
    tag_lookup = {t.label_or_description.strip(): t for t in result.tags}

    def find_tag(key: str):
        if key in tag_lookup:
            return tag_lookup[key]
        for k, t in tag_lookup.items():
            if key in k or k in key:
                return t
        return None

    label_to_node_id: dict[str, str] = {}
    tagged_nodes: list[GraphNode] = []
    for e in entities:
        tag = find_tag(e["label"]) or find_tag(e["description"])
        evidence_type = tag.evidence_type if tag else "inference"
        confidence = tag.confidence if tag else 0.5
        node = GraphNode(
            node_type=e["node_type"],
            label=e["label"],
            description=e["description"],
            source_chunk_ids=[chunk["chunk_id"]],
            evidence_type=evidence_type,
            confidence=confidence,
        )
        tagged_nodes.append(node)
        label_to_node_id[e["label"]] = node.node_id

    tagged_edges: list[GraphEdge] = []
    for e in edges:
        src_id = label_to_node_id.get(e["source_label"])
        tgt_id = label_to_node_id.get(e["target_label"])
        if not src_id or not tgt_id:
            continue  # edge refers to an entity we didn't keep; skip rather than guess
        tag = find_tag(e["description"])
        evidence_type = tag.evidence_type if tag else "inference"
        confidence = tag.confidence if tag else 0.5
        tagged_edges.append(
            GraphEdge(
                source_node_id=src_id,
                target_node_id=tgt_id,
                edge_type=e["edge_type"],
                description=e["description"],
                source_chunk_ids=[chunk["chunk_id"]],
                evidence_type=evidence_type,
                confidence=confidence,
            )
        )

    state["tagged_nodes"] = tagged_nodes
    state["tagged_edges"] = tagged_edges
    return state


# --- Node 4: contradiction check ---


def check_contradictions(state: ExtractionState) -> ExtractionState:
    """For each new node, check Chroma for an existing, semantically-similar node.
    If found, don't merge — flag a contradiction record for the UI to surface."""
    contradictions: list[ContradictionRecord] = []

    for node in state["tagged_nodes"]:
        embedding = embed_text(node.description)
        results = query_similar_nodes(embedding, k=3)
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        docs = results.get("documents", [[]])[0]

        for existing_id, distance, existing_desc in zip(ids, distances, docs):
            if existing_id == node.node_id:
                continue
            if distance <= CONTRADICTION_SIMILARITY_THRESHOLD:
                # Similar enough to be about the "same" fact — flag as a potential
                # contradiction for a human/UI to review, rather than silently merging.
                contradictions.append(
                    ContradictionRecord(
                        node_id_a=existing_id,
                        node_id_b=node.node_id,
                        note=(
                            f"New node '{node.label}' closely overlaps an existing node "
                            f"(distance={distance:.3f}). Existing: '{existing_desc[:120]}' vs "
                            f"new: '{node.description[:120]}'. Review for agreement/conflict."
                        ),
                    )
                )

    state["gaps"] = state.get("gaps", [])
    state["contradictions"] = contradictions
    return state


# --- Node 5: write to graph ---


def write_to_graph(state: ExtractionState) -> ExtractionState:
    for node in state["tagged_nodes"]:
        add_node_to_graph(node)
        add_node_to_chroma(node, embed_text(node.description))
    for edge in state["tagged_edges"]:
        add_edge_to_graph(edge)
    return state


def build_pipeline():
    workflow = StateGraph(ExtractionState)
    workflow.add_node("extract_entities", extract_entities)
    workflow.add_node("propose_edges", propose_edges)
    workflow.add_node("tag", tag_fact_inference_prediction)
    workflow.add_node("check_contradictions", check_contradictions)
    workflow.add_node("write_to_graph", write_to_graph)

    workflow.set_entry_point("extract_entities")
    workflow.add_edge("extract_entities", "propose_edges")
    workflow.add_edge("propose_edges", "tag")
    workflow.add_edge("tag", "check_contradictions")
    workflow.add_edge("check_contradictions", "write_to_graph")
    workflow.add_edge("write_to_graph", END)

    return workflow.compile()


def run_pipeline_on_chunk(pipeline, chunk: dict) -> ExtractionState:
    initial_state: ExtractionState = {
        "chunk": chunk,
        "entities": [],
        "proposed_edges": [],
        "tagged_nodes": [],
        "tagged_edges": [],
        "gaps": [],
        "contradictions": [],
    }
    return pipeline.invoke(initial_state)
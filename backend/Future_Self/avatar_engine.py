"""
Future Self avatar engine.

Grounds each reply in memory-graph precedents (chunk store) and the External
Evidence Layer, then produces text through the configured LLM provider when
available or a deterministic, clearly-labelled fallback. Never
crashes: any retrieval or LLM failure degrades gracefully.
"""

from __future__ import annotations

import statistics

from backend import config
from backend.logging_config import get_logger

from .avatar_schema import (
    AvatarChatRequest,
    AvatarChatResponse,
    AvatarCitation,
    GroundingLabel,
)

logger = get_logger(__name__)


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _retrieve_grounding(message: str, decision_question: str | None):
    """Best-effort retrieval of memory precedents + external evidence. Both sides
    fail soft (empty list) so the avatar always answers."""
    query = " ".join(p for p in [message, decision_question or ""] if p).strip()

    mem_items: list[dict] = []
    try:
        from backend.Decision_Graph.query_layer import find_similar_past_decisions_clean

        mem_items = find_similar_past_decisions_clean(query, k=3).get("items", [])
    except Exception:
        mem_items = []

    evidence = []
    try:
        from backend.External_Evidence.evidence_service import search_evidence

        evidence = search_evidence(query=query, k=3)
    except Exception:
        evidence = []

    return mem_items, evidence


def _grounding_label(mem_items: list, evidence: list) -> GroundingLabel:
    has_memory = bool(mem_items)
    has_evidence = bool(evidence)
    if has_memory and has_evidence:
        return "mixed"
    if has_memory:
        return "graph_grounded"
    if has_evidence:
        return "evidence_grounded"
    return "general_opinion"


def _confidence(label: GroundingLabel, mem_items: list, evidence: list) -> float:
    if label == "general_opinion":
        return 0.25
    count = len(mem_items) + len(evidence)
    avg_evidence_conf = (
        statistics.mean(e.confidence for e in evidence) if evidence else 0.6
    )
    return _clip01(0.35 + min(count, 4) / 4.0 * 0.35 + avg_evidence_conf * 0.2)


def _build_citations(mem_items: list, evidence: list) -> list[AvatarCitation]:
    citations: list[AvatarCitation] = []
    for m in mem_items:
        snippet = (m.get("snippet") or "").strip()
        citations.append(
            AvatarCitation(
                nodeId=m.get("chunk_id", "unknown"),
                label=(snippet[:80] or m.get("chunk_id", "memory")),
                excerpt=snippet or None,
            )
        )
    for e in evidence:
        citations.append(
            AvatarCitation(
                nodeId=e.id,
                label=e.title[:80],
                excerpt=e.summary,
                url=e.source_url,
            )
        )
    return citations


def _timeline_phrase(request: AvatarChatRequest) -> str:
    return request.selectedTimelineId or "the selected timeline"


def _build_prompt(request: AvatarChatRequest, mem_items: list, evidence: list, label: GroundingLabel) -> str:
    grounding_lines = []
    for m in mem_items:
        grounding_lines.append(f"- [memory:{m.get('chunk_id')}] {(m.get('snippet') or '')[:200]}")
    for e in evidence:
        grounding_lines.append(f"- [evidence:{e.id}] {e.title}: {e.summary[:200]}")
    grounding_block = "\n".join(grounding_lines) if grounding_lines else "(no grounding retrieved)"

    return (
        "You are the user's FUTURE SELF, speaking from within a specific simulated "
        f"timeline ({_timeline_phrase(request)}). Answer in the first person.\n\n"
        "Rules:\n"
        "- When you describe a simulated outcome, begin that claim with 'The simulation suggests...'.\n"
        "- When you reason without grounding, begin with 'General reasoning...' and say confidence is low.\n"
        "- Cite grounding items inline by their id (e.g. [memory:...] or [evidence:...]) when you use them.\n"
        "- Never invent market facts that are not in the grounding block.\n"
        "- Be concise (2-4 short paragraphs).\n\n"
        f"Decision under consideration: {request.decisionQuestion or 'unspecified'}\n"
        f"Grounding available ({label}):\n{grounding_block}\n\n"
        f"User asks: {request.message}\n\n"
        "Your answer as their Future Self:"
    )


def _llm_answer(request: AvatarChatRequest, mem_items: list, evidence: list, label: GroundingLabel):
    """Return LLM text, or None if the provider is unavailable/failed (caller
    then uses the deterministic fallback)."""
    try:
        from backend.LLM.llm_service import chat as llm_chat

        prompt = _build_prompt(request, mem_items, evidence, label)
        content = llm_chat(prompt, temperature=0.3)
        if isinstance(content, str) and content.strip():
            return content.strip()
        return None
    except Exception:
        logger.warning(
            "Configured LLM provider %s unavailable; using deterministic avatar fallback.",
            config.LLM_PROVIDER,
        )
        return None


def _fallback_answer(request: AvatarChatRequest, mem_items: list, evidence: list, label: GroundingLabel) -> str:
    """Deterministic, clearly-labelled response when the LLM is unavailable."""
    header = (
        f"_(Configured LLM provider '{config.LLM_PROVIDER}' is unavailable, so this is a deterministic, "
        "grounded fallback from your Future Self.)_\n\n"
    )

    if label == "general_opinion":
        return (
            header
            + f"General reasoning: within {_timeline_phrase(request)}, I don't have simulation "
            f"grounding or evidence specific to \"{request.message}\" yet, so treat this as **low "
            "confidence**. Based on general startup/decision heuristics, weigh reversibility and "
            "downside before committing, and revisit once more of your history is in the memory graph."
        )

    parts: list[str] = [header]
    parts.append(
        f"The simulation suggests, within {_timeline_phrase(request)}, that your question "
        f"\"{request.message}\" connects to grounding already in your Chronos context:"
    )

    if mem_items:
        closest = mem_items[0]
        parts.append(
            f"- From your memory graph [memory:{closest.get('chunk_id')}]: "
            f"\"{(closest.get('snippet') or '')[:160]}\"."
        )
    if evidence:
        top = evidence[0]
        parts.append(f"- From external evidence [evidence:{top.id}]: {top.title} — {top.summary[:160]}")

    parts.append(
        "I'm reasoning from that grounding rather than guessing. Once the LLM key is configured, "
        "I can expand this into a fuller narrative, but the cited nodes above are what actually "
        "anchors this answer."
    )
    return "\n\n".join(parts)


def generate_avatar_reply(request: AvatarChatRequest) -> AvatarChatResponse:
    mem_items, evidence = _retrieve_grounding(request.message, request.decisionQuestion)
    label = _grounding_label(mem_items, evidence)
    citations = _build_citations(mem_items, evidence)
    confidence = round(_confidence(label, mem_items, evidence), 3)

    content = _llm_answer(request, mem_items, evidence, label)
    llm_backed = content is not None
    if not content:
        content = _fallback_answer(request, mem_items, evidence, label)

    referenced = list(
        dict.fromkeys((request.graphNodeIds or []) + [c.nodeId for c in citations])
    )

    # Provenance: record this answer as an auditable ClaimRecord. Best-effort.
    claim_id = None
    try:
        from backend.Provenance.provenance_schema import ClaimRecord
        from backend.Provenance.provenance_service import create_claim

        uncertainty = (
            "No grounding retrieved — general reasoning, low confidence."
            if label == "general_opinion"
            else f"Grounded via {label}; heuristic, not a guaranteed outcome."
        )
        claim = create_claim(
            ClaimRecord(
                claim_text=content[:2000],
                claim_type="prediction" if label != "general_opinion" else "inference",
                created_by="avatar",
                source_ids=[m.get("chunk_id") for m in mem_items if m.get("chunk_id")],
                evidence_ids=[e.id for e in evidence],
                graph_node_ids=list(request.graphNodeIds or []),
                confidence=confidence,
                uncertainty_reason=uncertainty,
            )
        )
        claim_id = claim.claim_id
    except Exception:
        claim_id = None

    return AvatarChatResponse(
        content=content,
        referencedNodeIds=referenced,
        citations=citations,
        groundingLabel=label,
        confidence=confidence,
        llmBacked=llm_backed,
        claim_id=claim_id,
    )

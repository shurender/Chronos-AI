"""
Chronos multi-agent council — lightweight, deterministic, demo-ready.

Six agents each read from a shared context (decision intake, memory-graph
precedents, external demo evidence, heuristic forecast) and emit a structured
AgentOutput. Nothing here is autonomous or LLM-backed yet: outputs are pure
functions of the inputs, so identical inputs give identical council output.

TODO: swap individual agent bodies for Groq-backed reasoning (backend/llm.py)
once the deterministic contract is locked in.
"""

from __future__ import annotations

import hashlib
import statistics
import time

from backend.Digital_Twin.digital_twin_schema import DigitalTwinProfile
from backend.External_Evidence.evidence_schema import EvidenceItem
from backend.simulation_schema import AgentDisagreement, SimulationRequest, TimelineBranch

from .agent_schema import (
    AgentCouncil,
    AgentOutput,
    AgentRunTrace,
    LLMAgentEnrichment,
)

# Tags that lean a market signal toward "act" vs "hold" — used only to derive a
# direction from evidence the MarketAgent was actually given (never invented).
_POSITIVE_EVIDENCE_TAGS = {"adoption", "product_led", "b2b2c", "breakout", "pull", "traction"}
_NEGATIVE_EVIDENCE_TAGS = {"risk", "failure", "runway", "competition", "regulatory", "compliance"}


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


# --- Individual agents. Each returns (AgentOutput, lean) where lean in [-1, 1]
#     is the agent's directional stance: +1 favors acting, -1 favors caution. ---


def _historian(request: SimulationRequest, precedents: list[dict]) -> tuple[AgentOutput, float]:
    if not precedents:
        return (
            AgentOutput(
                agent_id="historian",
                agent_label="Historian Agent",
                position=(
                    "No closely similar past decisions were found in your memory graph, "
                    "so historical grounding for this choice is weak."
                ),
                confidence=0.25,
                rationale=[
                    "Memory graph returned no near-neighbour precedents for this decision.",
                    "A base rate cannot be estimated from your own history yet.",
                ],
                citations=[],
                concerns=["No historical precedent — treat forecasts as lightly grounded."],
            ),
            0.0,
        )

    citations = [p.get("chunk_id") for p in precedents[:5] if p.get("chunk_id")]
    avg_distance = statistics.mean(p.get("distance", 1.0) for p in precedents)
    grounding = _clip01(1.0 - avg_distance)
    closest = precedents[0].get("snippet", "")[:140]

    return (
        AgentOutput(
            agent_id="historian",
            agent_label="Historian Agent",
            position=(
                f"Found {len(precedents)} similar past decision(s) in your memory graph; "
                f"the closest reads: \"{closest}\"."
            ),
            confidence=_clip01(0.35 + grounding * 0.5),
            rationale=[
                f"Average semantic distance to prior decisions: {avg_distance:.2f} (closer = stronger analogy).",
                "Historical analogues give the forecast some grounding beyond pure heuristics.",
            ],
            citations=citations,
            concerns=(
                [] if grounding > 0.35 else ["Precedents are only loosely similar; analogy may be weak."]
            ),
        ),
        0.2,
    )


def _behavioral(
    request: SimulationRequest,
    precedents: list[dict],
    twin: DigitalTwinProfile | None = None,
) -> tuple[AgentOutput, float]:
    twin_signal = bool(twin and (twin.behavioral_patterns or twin.execution_style.style != "insufficient data"))

    if not precedents and not twin_signal:
        return (
            AgentOutput(
                agent_id="behavioral",
                agent_label="Behavioral Agent",
                position=(
                    "Not enough personal history to infer your decision style or execution pattern."
                ),
                confidence=0.2,
                rationale=[
                    "No prior decisions available to model risk tendency or follow-through.",
                ],
                citations=[],
                concerns=["Behavioral profile unavailable; any inference would be speculative."],
            ),
            0.0,
        )

    risk = request.risk
    if risk >= 66:
        tendency = "risk-seeking, willing to accept volatility for upside"
    elif risk <= 33:
        tendency = "risk-averse, favoring reversible, incremental moves"
    else:
        tendency = "balanced, weighing upside and downside roughly evenly"

    coverage = _clip01(len(precedents) / 3.0)
    citations = [p.get("chunk_id") for p in precedents[:3] if p.get("chunk_id")]

    position = (
        f"Your stated risk tolerance ({risk}/100) and {len(precedents)} prior decision(s) "
        f"suggest a {tendency} execution style."
    )
    rationale = [
        f"Risk tolerance {risk}/100 maps to a {tendency.split(',')[0]} profile.",
        "Inference is weighted by how much personal history is available.",
    ]
    confidence = _clip01(0.25 + coverage * 0.45)
    concerns = [] if coverage >= 0.66 else ["Limited history — behavioral read is provisional."]

    if twin_signal:
        position += f" Digital twin profile ({twin.subject_type}) reads: {twin.execution_style.style}."
        rationale.append(f"Digital twin execution style: {twin.execution_style.style}.")
        for pattern in twin.behavioral_patterns[:2]:
            rationale.append(f"Twin behavioral signal: {pattern.label} (confidence {pattern.confidence:.2f}).")
            citations.extend(pattern.citations)
        citations = list(dict.fromkeys(citations))
        # Independent corroboration from the twin lifts confidence and clears
        # the "provisional" flag even when the raw precedent count is thin.
        confidence = _clip01(confidence + 0.15)
        concerns = [c for c in concerns if c != "Limited history — behavioral read is provisional."]

    return (
        AgentOutput(
            agent_id="behavioral",
            agent_label="Behavioral Agent",
            position=position,
            confidence=confidence,
            rationale=rationale,
            citations=citations,
            concerns=concerns,
        ),
        (risk - 50) / 50.0 * 0.6,
    )


def _domain(request: SimulationRequest) -> tuple[AgentOutput, float]:
    goal = (request.goal or "").strip() or "the stated goal"
    if request.type == "Startup":
        position = (
            f"For a startup decision, the pivotal fit questions are product/market pull, "
            f"resource runway, and team capacity relative to \"{goal}\"."
        )
        rationale = [
            "Startup outcomes hinge on product/market fit and resource fit more than intent.",
            "Resource fit (runway, hiring) gates how many iterations you get.",
        ]
    elif request.type == "Career":
        position = (
            f"For a career decision, the core question is skill/market fit: whether your skills "
            f"compound toward \"{goal}\" in a growing market."
        )
        rationale = [
            "Career outcomes track skill/market fit and compounding over single moves.",
            "A growing market forgives execution mistakes a shrinking one punishes.",
        ]
    else:
        position = (
            f"For a {request.type.lower()} decision, weigh fit between your resources, timing, "
            f"and \"{goal}\" against the reversibility of the choice."
        )
        rationale = [
            f"{request.type} decisions turn on fit and reversibility more than on forecast precision.",
        ]

    return (
        AgentOutput(
            agent_id="domain",
            agent_label="Domain Agent",
            position=position,
            confidence=0.55,
            rationale=rationale,
            citations=[],
            concerns=[],
        ),
        0.1,
    )


def _market(evidence: list[EvidenceItem]) -> tuple[AgentOutput, float]:
    if not evidence:
        return (
            AgentOutput(
                agent_id="market",
                agent_label="Market Agent",
                position=(
                    "No external evidence is available for this decision, so I will not assert "
                    "any market claim."
                ),
                confidence=0.2,
                rationale=[
                    "This agent reports only what is in the External Evidence Layer; it does not invent market claims.",
                ],
                citations=[],
                concerns=["No external evidence — the market view is unsupported."],
            ),
            0.0,
        )

    avg_conf = statistics.mean(e.confidence for e in evidence)
    citations = [e.id for e in evidence[:5]]
    top = evidence[0]

    all_tags = {t.lower() for e in evidence for t in e.tags}
    pos_hits = len(all_tags & _POSITIVE_EVIDENCE_TAGS)
    neg_hits = len(all_tags & _NEGATIVE_EVIDENCE_TAGS)
    total = pos_hits + neg_hits
    lean = ((pos_hits - neg_hits) / total) if total else 0.0

    # Distinguish provenance: demo vs uploaded vs live. MarketAgent must be
    # explicit that demo/uploaded evidence is NOT live web data.
    demo_n = sum(1 for e in evidence if e.is_demo_source)
    uploaded_n = sum(1 for e in evidence if e.source_kind == "uploaded")
    live_n = sum(1 for e in evidence if e.is_live_source)
    kind_bits = []
    if demo_n:
        kind_bits.append(f"{demo_n} demo")
    if uploaded_n:
        kind_bits.append(f"{uploaded_n} uploaded")
    if live_n:
        kind_bits.append(f"{live_n} live")
    provenance = ", ".join(kind_bits) or "unknown"

    concerns = [] if len(evidence) >= 3 else ["Thin evidence base — market read is directional only."]
    if live_n == 0:
        concerns.append("No live web evidence — findings rest on demo/uploaded sources only.")

    return (
        AgentOutput(
            agent_id="market",
            agent_label="Market Agent",
            position=(
                f"{len(evidence)} external evidence item(s) are relevant ({provenance}). "
                f"Strongest signal: \"{top.title}\"."
            ),
            confidence=_clip01(0.35 + avg_conf * 0.5),
            rationale=[
                f"Average confidence of cited evidence: {avg_conf:.0%}.",
                f"Evidence provenance: {provenance}. Claims come only from the External Evidence Layer, not model priors.",
            ],
            citations=citations,
            concerns=concerns,
        ),
        lean * 0.8,
    )


def _risk(
    request: SimulationRequest,
    forecast_context: dict,
    precedents: list[dict],
    evidence: list[EvidenceItem],
    twin: DigitalTwinProfile | None = None,
    intake_missing_fields: list[str] | None = None,
) -> tuple[AgentOutput, float]:
    failure = float(forecast_context.get("failure_share", 0.0))
    top_risks = forecast_context.get("top_risks", []) or []

    concerns: list[str] = []
    if not precedents:
        concerns.append("No historical precedents in your graph — sparse evidence, base rate unknown.")
    if not evidence:
        concerns.append("No external evidence — market risk is unquantified.")
    if request.constraints:
        concerns.append(f"Stated constraint to respect: {request.constraints}.")
    if failure >= 30:
        concerns.append(f"Modeled failure share is elevated ({failure:.0f}%).")
    for field in (intake_missing_fields or [])[:4]:
        concerns.append(f"Missing decision context: {field} (Chronos is assuming a default).")

    citations = [p.get("chunk_id") for p in precedents[:2] if p.get("chunk_id")]
    position = (
        f"Modeled failure share is {failure:.0f}%. Primary pressure points: "
        f"{', '.join(top_risks) if top_risks else 'n/a'}."
    )
    confidence = _clip01(0.5 + failure / 200.0)

    if twin:
        # RiskAgent's job is to surface gaps, not hide them — so the twin's own
        # missing_information/contradictions become concerns here, verbatim.
        concerns.extend(f"Digital twin gap: {gap}" for gap in twin.missing_information[:3])
        concerns.extend(f"Digital twin contradiction: {c}" for c in twin.contradictions[:2])
        if twin.risk_profile.level != "unknown":
            position += f" Digital twin risk profile: {twin.risk_profile.level} (score {twin.risk_profile.score:.2f})."
            blended = _clip01((failure / 100.0) * 0.6 + twin.risk_profile.score * 0.4)
            confidence = _clip01(0.5 + blended / 2.0)
            citations.extend(twin.source_chunk_ids[:3])
        citations = list(dict.fromkeys(citations))

    if not concerns:
        concerns.append("No blocking gaps detected, but forecasts remain heuristic.")

    return (
        AgentOutput(
            agent_id="risk",
            agent_label="Risk Agent",
            position=position,
            confidence=confidence,
            rationale=[
                "Downside is estimated from the heuristic forecast, not observed outcomes.",
                "Missing precedents or evidence widen the true uncertainty band.",
            ],
            citations=citations,
            concerns=concerns,
        ),
        -_clip01(failure / 100.0),
    )


def _strategist(
    request: SimulationRequest,
    branches: list[TimelineBranch],
    recommended_branch_id: str,
    analysts: list[AgentOutput],
    consensus: float,
    intake_low_completeness: bool = False,
) -> tuple[AgentOutput, float]:
    rec = next((b for b in branches if b.id == recommended_branch_id), branches[0] if branches else None)

    # Preserve (not hide) disagreement: name the most cautious dissenting agent.
    dissenters = [a for a in analysts if a.concerns]
    dissent_note = (
        f"{dissenters[0].agent_label} flags: {dissenters[0].concerns[0]}"
        if dissenters
        else "No agent raised a blocking concern."
    )

    # Rank branches by the same probability-vs-regret score used to recommend,
    # so the recommendation can name what it beat (explainable, option-aware).
    ranked = sorted(
        branches, key=lambda b: b.probabilityScore * 0.6 - b.expectedRegret * 0.4, reverse=True
    )
    runner_up = next((b for b in ranked if b.id != recommended_branch_id), None)

    if rec is None:
        position = "No branches were generated to recommend."
        confidence = 0.2
    else:
        compare = (
            f" Chosen over {runner_up.title} ({runner_up.probabilityScore * 100:.0f}% / "
            f"regret {runner_up.expectedRegret * 100:.0f}%)."
            if runner_up
            else ""
        )
        position = (
            f"Recommended among {len(branches)} option(s): {rec.title} "
            f"(probability {rec.probabilityScore * 100:.0f}%, expected regret {rec.expectedRegret * 100:.0f}%)."
            f"{compare} {dissent_note}"
        )
        if intake_low_completeness:
            position += " This recommendation is provisional — key decision context is missing."
        confidence = _clip01(0.35 + rec.probabilityScore * 0.4 + consensus * 0.25)

    concerns = []
    if consensus < 0.5:
        concerns.append("Council is divided; treat the recommendation as provisional.")
    if intake_low_completeness:
        concerns.append("Recommendation rests on assumed context (low intake completeness).")

    citations = sorted({c for a in analysts for c in a.citations})[:6]

    return (
        AgentOutput(
            agent_id="strategist",
            agent_label="Strategist Agent",
            position=position,
            confidence=confidence,
            rationale=[
                "Chose the branch with the best probability-vs-regret tradeoff.",
                f"Council consensus across analyst agents: {consensus:.0%}.",
            ],
            citations=citations,
            concerns=concerns,
        ),
        (rec.probabilityScore - rec.expectedRegret) if rec else 0.0,
    )


def _consensus(analysts: list[tuple[AgentOutput, float]]) -> float:
    """Model consensus from agent AGREEMENT (directional spread) and confidence."""
    if not analysts:
        return 0.0
    confidences = [o.confidence for o, _ in analysts]
    leans = [lean for _, lean in analysts]
    mean_conf = statistics.mean(confidences)
    lean_spread = statistics.pstdev(leans) if len(leans) > 1 else 0.0  # leans in [-1, 1]
    directional_agreement = _clip01(1.0 - lean_spread)
    return _clip01(0.45 * mean_conf + 0.55 * directional_agreement)


# ---------------------------------------------------------------------------
# Optional LLM enrichment (AGENT_MODE=llm|hybrid). Deterministic output above is
# always the baseline and the fallback — bad/empty LLM output cannot break it.
# ---------------------------------------------------------------------------

_AGENT_ROLES = {
    "historian": "You are the Historian: reason ONLY from the provided historical precedents.",
    "behavioral": "You are the Behavioral analyst: infer decision/execution style from the digital twin and history.",
    "domain": "You are the Domain expert for this decision type.",
    "market": "You are the Market analyst: use ONLY the provided evidence snapshot; NEVER invent market facts. If evidence is thin, say so.",
    "risk": "You are the Risk analyst: surface downside, missing evidence, and uncertainty explicitly.",
    "strategist": "You are the Strategist: synthesize and recommend, but PRESERVE dissent — never hide uncertainty.",
}


def _allowed_citation_ids(
    evidence: list[EvidenceItem], precedents: list[dict], branches: list[TimelineBranch]
) -> set[str]:
    ids: set[str] = {e.id for e in evidence}
    ids |= {p.get("chunk_id") for p in precedents if p.get("chunk_id")}
    ids |= {nid for b in branches for nid in b.anchorNodeIds}
    return ids


def _build_agent_prompt(agent_id: str, det: AgentOutput, context_text: str, allowed_ids: set[str]) -> str:
    return (
        f"{_AGENT_ROLES.get(agent_id, 'You are a decision analyst.')}\n\n"
        "Enrich the baseline analysis below. Hard rules:\n"
        "- Cite ONLY from these allowed ids; never invent ids: "
        f"{sorted(allowed_ids)[:20]}\n"
        "- Make no factual claim you cannot ground in the provided context.\n"
        "- Keep or add concerns; never remove uncertainty or dissent.\n"
        "- Return JSON: position(str), rationale(list[str]), concerns(list[str]), "
        "citations(list[str]), confidence(0-1).\n\n"
        f"Baseline position: {det.position}\n"
        f"Baseline concerns: {det.concerns}\n\n"
        f"Decision context:\n{context_text}"
    )


def _merge_enrichment(
    det: AgentOutput, enrichment: LLMAgentEnrichment, allowed_ids: set[str], mode: str
) -> AgentOutput:
    # Guardrail: citations restricted to the allowed provenance pool.
    llm_citations = [c for c in enrichment.citations if c in allowed_ids]
    citations = list(dict.fromkeys(list(det.citations) + llm_citations))
    # Deterministic concerns are always preserved (RiskAgent missing-context,
    # Strategist dissent), then merged with any LLM concerns.
    concerns = list(dict.fromkeys(list(det.concerns) + [c for c in enrichment.concerns if c.strip()]))

    llm_pos = (enrichment.position or "").strip()
    llm_rationale = [r for r in enrichment.rationale if r.strip()]

    if mode == "hybrid":
        # Deterministic baseline stays authoritative; LLM only appends rationale.
        position = det.position
        rationale = list(dict.fromkeys(list(det.rationale) + llm_rationale))
        confidence = (
            det.confidence if enrichment.confidence is None else _clip01((det.confidence + enrichment.confidence) / 2)
        )
    else:  # "llm"
        position = llm_pos or det.position  # keep deterministic if LLM empty
        rationale = llm_rationale or list(det.rationale)
        confidence = det.confidence if enrichment.confidence is None else _clip01(enrichment.confidence)

    return AgentOutput(
        agent_id=det.agent_id,
        agent_label=det.agent_label,
        position=position,
        confidence=confidence,
        rationale=rationale,
        citations=citations,
        concerns=concerns,
    )


def _enrich_with_llm(
    det: AgentOutput, context_text: str, allowed_ids: set[str], mode: str
) -> tuple[AgentOutput, AgentRunTrace]:
    """Enrich one deterministic AgentOutput with the LLM. Any failure (provider
    down, invalid/unparseable output) falls back to the deterministic output and
    is recorded in the trace — it can never raise."""
    from backend import config
    from backend.LLM import llm_service

    provider = config.LLM_PROVIDER
    model = ""
    prompt = _build_agent_prompt(det.agent_id, det, context_text, allowed_ids)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    input_summary = f"{det.agent_id}: {context_text[:120]}"

    t0 = time.perf_counter()
    output, valid, fallback = det, False, True
    try:
        try:
            model = getattr(llm_service.get_chat_provider(), "model_name", "") or ""
        except Exception:
            model = ""
        enrichment = llm_service.chat(prompt, temperature=0.2, response_schema=LLMAgentEnrichment)
        if isinstance(enrichment, LLMAgentEnrichment):
            output = _merge_enrichment(det, enrichment, allowed_ids, mode)
            valid, fallback = True, False
    except Exception:
        output, valid, fallback = det, False, True

    trace = AgentRunTrace(
        agent_id=det.agent_id,
        provider=provider,
        model=model,
        prompt_hash=prompt_hash,
        input_summary=input_summary[:200],
        output_valid=valid,
        fallback_used=fallback,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
    return output, trace


def _council_context_text(
    request: SimulationRequest,
    precedents: list[dict],
    evidence: list[EvidenceItem],
    branches: list[TimelineBranch],
    twin: DigitalTwinProfile | None,
) -> str:
    parts = [f"Decision: {request.name} (type={request.type}, horizon={request.horizon}, goal={request.goal})."]
    if twin:
        parts.append(
            f"Digital twin: {twin.subject_type}, risk={twin.risk_profile.level}, "
            f"execution={twin.execution_style.style}."
        )
    parts.append(
        "Precedents: "
        + ("; ".join(f"[{p.get('chunk_id')}] {(p.get('snippet') or '')[:80]}" for p in precedents[:3]) or "none")
    )
    parts.append(
        "Evidence snapshot: "
        + ("; ".join(f"[{e.id}] {e.title}" for e in evidence[:4]) or "none")
    )
    parts.append("Branches: " + "; ".join(f"{b.title} ({b.probabilityScore:.0%})" for b in branches[:4]))
    return "\n".join(parts)


def run_agent_council(
    request: SimulationRequest,
    precedents: list[dict],
    evidence: list[EvidenceItem],
    branches: list[TimelineBranch],
    recommended_branch_id: str,
    forecast_context: dict,
    twin: DigitalTwinProfile | None = None,
    intake_missing_fields: list[str] | None = None,
    intake_low_completeness: bool = False,
    agent_mode: str = "deterministic",
) -> AgentCouncil:
    analysts = [
        _historian(request, precedents),
        _behavioral(request, precedents, twin),
        _domain(request),
        _market(evidence),
        _risk(request, forecast_context, precedents, evidence, twin, intake_missing_fields),
    ]

    consensus = _consensus(analysts)  # kept deterministic/numeric for stability

    strategist_output, _ = _strategist(
        request,
        branches,
        recommended_branch_id,
        [o for o, _ in analysts],
        consensus,
        intake_low_completeness,
    )

    agents = [o for o, _ in analysts] + [strategist_output]
    mode = (agent_mode or "deterministic").strip().lower()
    traces: list[AgentRunTrace] = []

    if mode in ("llm", "hybrid"):
        allowed_ids = _allowed_citation_ids(evidence, precedents, branches)
        context_text = _council_context_text(request, precedents, evidence, branches, twin)
        enriched: list[AgentOutput] = []
        for det in agents:
            # MarketAgent guardrail: with no evidence, never let the LLM assert a
            # market claim — keep the deterministic refusal.
            if det.agent_id == "market" and not evidence:
                enriched.append(det)
                traces.append(
                    AgentRunTrace(
                        agent_id="market",
                        provider="(skipped)",
                        model="",
                        output_valid=False,
                        fallback_used=True,
                        input_summary="no evidence — deterministic refusal kept",
                    )
                )
                continue
            out, trace = _enrich_with_llm(det, context_text, allowed_ids, mode)
            enriched.append(out)
            traces.append(trace)
        agents = enriched

    is_deterministic = not any(not t.fallback_used for t in traces)
    summary = (
        f"{len(agents)} agents evaluated this decision (mode={mode}); consensus "
        f"{consensus:.0%}. {agents[-1].position if agents else ''}"
    )

    return AgentCouncil(
        agents=agents,
        recommendedBranchId=recommended_branch_id,
        consensusScore=round(consensus, 3),
        summary=summary,
        mode=mode,
        isDeterministic=is_deterministic,
        traces=traces,
    )


def council_to_disagreements(council: AgentCouncil) -> list[AgentDisagreement]:
    """Map council outputs onto the existing per-timeline AgentDisagreement shape."""
    return [
        AgentDisagreement(
            agentId=o.agent_id,
            agentLabel=o.agent_label,
            position=o.position,
            confidence=o.confidence,
            rationale=list(o.rationale) + [f"Concern: {c}" for c in o.concerns],
        )
        for o in council.agents
    ]

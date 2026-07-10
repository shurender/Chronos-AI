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

import statistics

from backend.External_Evidence.evidence_schema import EvidenceItem
from backend.schema import AgentDisagreement, SimulationRequest, TimelineBranch

from .agent_schema import AgentCouncil, AgentOutput

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


def _behavioral(request: SimulationRequest, precedents: list[dict]) -> tuple[AgentOutput, float]:
    if not precedents:
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

    return (
        AgentOutput(
            agent_id="behavioral",
            agent_label="Behavioral Agent",
            position=(
                f"Your stated risk tolerance ({risk}/100) and {len(precedents)} prior decision(s) "
                f"suggest a {tendency} execution style."
            ),
            confidence=_clip01(0.25 + coverage * 0.45),
            rationale=[
                f"Risk tolerance {risk}/100 maps to a {tendency.split(',')[0]} profile.",
                "Inference is weighted by how much personal history is available.",
            ],
            citations=citations,
            concerns=(
                [] if coverage >= 0.66 else ["Limited history — behavioral read is provisional."]
            ),
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

    return (
        AgentOutput(
            agent_id="market",
            agent_label="Market Agent",
            position=(
                f"{len(evidence)} external evidence item(s) are relevant. Strongest signal: "
                f"\"{top.title}\"."
            ),
            confidence=_clip01(0.35 + avg_conf * 0.5),
            rationale=[
                f"Average confidence of cited evidence: {avg_conf:.0%}.",
                "All claims are grounded in the External Evidence Layer (demo pack), not model priors.",
            ],
            citations=citations,
            concerns=(
                [] if len(evidence) >= 3 else ["Thin evidence base — market read is directional only."]
            ),
        ),
        lean * 0.8,
    )


def _risk(
    request: SimulationRequest,
    forecast_context: dict,
    precedents: list[dict],
    evidence: list[EvidenceItem],
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
    if not concerns:
        concerns.append("No blocking gaps detected, but forecasts remain heuristic.")

    citations = [p.get("chunk_id") for p in precedents[:2] if p.get("chunk_id")]

    return (
        AgentOutput(
            agent_id="risk",
            agent_label="Risk Agent",
            position=(
                f"Modeled failure share is {failure:.0f}%. Primary pressure points: "
                f"{', '.join(top_risks) if top_risks else 'n/a'}."
            ),
            confidence=_clip01(0.5 + failure / 200.0),
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
) -> tuple[AgentOutput, float]:
    rec = next((b for b in branches if b.id == recommended_branch_id), branches[0] if branches else None)

    # Preserve (not hide) disagreement: name the most cautious dissenting agent.
    dissenters = [a for a in analysts if a.concerns]
    dissent_note = (
        f"{dissenters[0].agent_label} flags: {dissenters[0].concerns[0]}"
        if dissenters
        else "No agent raised a blocking concern."
    )

    if rec is None:
        position = "No branches were generated to recommend."
        confidence = 0.2
    else:
        position = (
            f"Recommended path: {rec.title} "
            f"(probability {rec.probabilityScore * 100:.0f}%, expected regret {rec.expectedRegret * 100:.0f}%). "
            f"{dissent_note}"
        )
        confidence = _clip01(0.35 + rec.probabilityScore * 0.4 + consensus * 0.25)

    concerns = []
    if consensus < 0.5:
        concerns.append("Council is divided; treat the recommendation as provisional.")

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


def run_agent_council(
    request: SimulationRequest,
    precedents: list[dict],
    evidence: list[EvidenceItem],
    branches: list[TimelineBranch],
    recommended_branch_id: str,
    forecast_context: dict,
) -> AgentCouncil:
    analysts = [
        _historian(request, precedents),
        _behavioral(request, precedents),
        _domain(request),
        _market(evidence),
        _risk(request, forecast_context, precedents, evidence),
    ]

    consensus = _consensus(analysts)

    strategist_output, _ = _strategist(
        request, branches, recommended_branch_id, [o for o, _ in analysts], consensus
    )

    agents = [o for o, _ in analysts] + [strategist_output]

    summary = (
        f"{len(agents)} deterministic agents evaluated this decision; consensus "
        f"{consensus:.0%}. {strategist_output.position}"
    )

    return AgentCouncil(
        agents=agents,
        recommendedBranchId=recommended_branch_id,
        consensusScore=round(consensus, 3),
        summary=summary,
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

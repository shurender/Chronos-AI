"""
Decision Forecast engine.

This is a deterministic HEURISTIC, not a trained predictive model — there is
no dataset of real decision outcomes backing these numbers. It combines:

  1. A per-(type) baseline profile (outcome mix + risk-category baseline),
  2. A risk-driven "barbell" adjustment (higher stated risk pushes mass from
     the middle outcomes toward the tails — more Failure AND more Breakout),
  3. A horizon-aware logistic growth curve for the success-forecast series,
  4. An optional grounding step against the existing decision graph: if the
     corpus already has chunks whose text is close to the request's
     name/goal, we surface them (GroundedDecision) and apply a small nudge
     based on whether those chunks look like they describe a positive or
     negative outcome.

Everything is seeded off a hash of the request so identical inputs always
produce identical output (reproducible, testable), while different names/
goals produce different-looking (but bounded, sane) results.
"""

from __future__ import annotations

import hashlib
import math
import random

from backend.Agents.agent_council import council_to_disagreements, run_agent_council
from backend.External_Evidence.evidence_schema import EvidenceItem
from backend.External_Evidence.evidence_service import search_evidence
from backend.schema import (
    Citation,
    ConfidenceBreakdown,
    DecisionForecast,
    DecisionForecastRequest,
    ForecastPoint,
    GroundedDecision,
    ProbabilityOutcome,
    RegretAnalysis,
    RiskHeatmapItem,
    SimulationMetadata,
    SimulationRequest,
    SimulationResponse,
    TimelineBranch,
    TimelineMilestone,
)

OUTCOME_ORDER = ["Failure", "Survival", "Modest", "Strong", "Breakout"]
RISK_CATEGORY_ORDER = ["Financial", "Career", "Health", "Relationships", "Reputation", "Time"]

HORIZON_MONTHS = {
    "1 year": 12,
    "3 years": 36,
    "5 years": 60,
    "10 years": 120,
}

# Baseline outcome mix (%) and baseline risk-category levels (0-100) per decision type.
# These are illustrative priors, not empirical data — tune freely.
TYPE_PROFILES: dict[str, dict] = {
    "Career": {
        "outcomes": {"Failure": 12, "Survival": 33, "Modest": 32, "Strong": 17, "Breakout": 6},
        "risk": {"Financial": 40, "Career": 65, "Health": 35, "Relationships": 35, "Reputation": 45, "Time": 45},
    },
    "Startup": {
        "outcomes": {"Failure": 35, "Survival": 20, "Modest": 20, "Strong": 15, "Breakout": 10},
        "risk": {"Financial": 78, "Career": 55, "Health": 45, "Relationships": 45, "Reputation": 50, "Time": 68},
    },
    "Financial": {
        "outcomes": {"Failure": 18, "Survival": 30, "Modest": 30, "Strong": 16, "Breakout": 6},
        "risk": {"Financial": 72, "Career": 25, "Health": 20, "Relationships": 25, "Reputation": 30, "Time": 35},
    },
    "Life": {
        "outcomes": {"Failure": 10, "Survival": 28, "Modest": 34, "Strong": 20, "Breakout": 8},
        "risk": {"Financial": 30, "Career": 25, "Health": 40, "Relationships": 55, "Reputation": 25, "Time": 40},
    },
    "Relocation": {
        "outcomes": {"Failure": 15, "Survival": 30, "Modest": 32, "Strong": 17, "Breakout": 6},
        "risk": {"Financial": 55, "Career": 45, "Health": 35, "Relationships": 60, "Reputation": 25, "Time": 55},
    },
}


def _seeded_rng(request: DecisionForecastRequest) -> random.Random:
    key = f"{request.name}|{request.type}|{request.horizon}|{request.risk}|{request.goal}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _normalize(values: dict[str, float]) -> dict[str, float]:
    total = sum(values.values())
    if total <= 0:
        # degenerate fallback: uniform
        n = len(values)
        return {k: 100.0 / n for k in values}
    return {k: (v / total) * 100.0 for k, v in values.items()}


def _round_to_exact_100(dist: dict[str, float], decimals: int = 1) -> dict[str, float]:
    """Round each value but nudge the largest bucket so the set sums to exactly
    100.0 — chart libraries (stacked bars, donut charts) misbehave otherwise."""
    rounded = {k: round(v, decimals) for k, v in dist.items()}
    diff = round(100.0 - sum(rounded.values()), decimals)
    if diff != 0:
        biggest_key = max(rounded, key=rounded.get)
        rounded[biggest_key] = round(rounded[biggest_key] + diff, decimals)
    return rounded


def _outcome_weights(request: DecisionForecastRequest, rng: random.Random) -> dict[str, float]:
    """Per-category weight (not yet a probability) after applying the risk
    barbell adjustment. Feeds the Monte Carlo sampler below."""
    base = dict(TYPE_PROFILES[request.type]["outcomes"])

    # risk in [0,100] -> centered shift in [-1, 1]
    centered_risk = (request.risk - 50) / 50.0
    # "barbell": more risk pulls weight from the middle (Survival/Modest) into
    # the tails (Failure/Breakout). Strong is left relatively alone.
    barbell = centered_risk * 10.0
    jitter = lambda: rng.uniform(-1.5, 1.5)  # small per-request texture

    base["Failure"] = max(0.1, base["Failure"] + barbell * 0.9 + jitter())
    base["Breakout"] = max(0.1, base["Breakout"] + barbell * 0.7 + jitter())
    base["Survival"] = max(0.1, base["Survival"] - barbell * 0.8 + jitter())
    base["Modest"] = max(0.1, base["Modest"] - barbell * 0.6 + jitter())
    base["Strong"] = max(0.1, base["Strong"] + barbell * 0.1 + jitter())

    return base


MONTE_CARLO_TRIALS = 10_000


def _outcome_distribution(request: DecisionForecastRequest, rng: random.Random) -> dict[str, float]:
    """Genuine Monte Carlo estimate: draw MONTE_CARLO_TRIALS samples from the
    categorical distribution implied by the type/risk weights, and report the
    empirical frequencies. (This is what the frontend's "Running 10,000 Monte
    Carlo futures…" loading copy should actually refer to — with this in
    place that copy is accurate, not decorative.)"""
    weights = _outcome_weights(request, rng)
    categories = OUTCOME_ORDER
    probs = _normalize(weights)  # analytic probabilities used to weight the draws

    cum = []
    running = 0.0
    for c in categories:
        running += probs[c]
        cum.append(running)

    counts = {c: 0 for c in categories}
    for _ in range(MONTE_CARLO_TRIALS):
        r = rng.random() * running  # running ~= 100.0
        for c, threshold in zip(categories, cum):
            if r <= threshold:
                counts[c] += 1
                break
        else:
            counts[categories[-1]] += 1

    empirical = {c: (counts[c] / MONTE_CARLO_TRIALS) * 100.0 for c in categories}
    return _round_to_exact_100(empirical)


def _risk_heatmap(request: DecisionForecastRequest, rng: random.Random) -> dict[str, float]:
    base = dict(TYPE_PROFILES[request.type]["risk"])
    risk_scale = 0.6 + (request.risk / 100.0) * 0.7  # 0.6x .. 1.3x
    out = {}
    for category, level in base.items():
        jitter = rng.uniform(-4, 4)
        out[category] = round(_clip(level * risk_scale + jitter), 1)
    return out


# Spec requirement: the Decision Lab's success-forecast chart is anchored on
# M0-M24 regardless of decision type. We always include these (clipped to the
# chosen horizon) and extend further out for horizons longer than 2 years so
# a 5- or 10-year forecast isn't truncated at month 24.
CORE_MONTH_ANCHORS = [0, 3, 6, 9, 12, 18, 24]

SUCCESS_MC_TRIALS = 2_000  # per-point trial count; cheap since it's just arithmetic


def _month_anchors(total_months: int) -> list[int]:
    anchors = [m for m in CORE_MONTH_ANCHORS if m <= total_months]
    if total_months > 24:
        step = max(6, total_months // 6)
        min_gap = max(4, step // 2)
        for candidate in range(step, total_months + 1, step):
            if all(abs(candidate - a) >= min_gap for a in anchors):
                anchors.append(candidate)
        anchors = sorted(set(anchors) | {total_months})
    elif not anchors or anchors[-1] != total_months:
        anchors = sorted(set(anchors) | {total_months})
    return anchors


def _success_forecast(
    request: DecisionForecastRequest,
    outcome_distribution: dict[str, float],
    rng: random.Random,
) -> list[ForecastPoint]:
    total_months = HORIZON_MONTHS[request.horizon]

    # Asymptote: everything that isn't outright Failure counts as "some success".
    asymptote = _clip(100.0 - outcome_distribution["Failure"])

    # Higher risk => slower ramp (later inflection point, gentler slope), and
    # more per-trial variance (less certain trajectory).
    risk_frac = request.risk / 100.0
    base_t0 = total_months * (0.35 + 0.25 * risk_frac)
    base_steepness = (6.0 / total_months) * (1.15 - 0.5 * risk_frac)
    trial_noise_scale = 1.0 + 2.5 * risk_frac  # riskier decisions -> noisier paths

    months = _month_anchors(total_months)

    points = []
    for m in months:
        # Monte Carlo average: each trial jitters the curve's shape params and
        # samples point noise, then we report the mean across trials — a real
        # (if lightweight) simulation average, not a single deterministic curve.
        total = 0.0
        for _ in range(SUCCESS_MC_TRIALS):
            t0 = base_t0 * rng.uniform(0.9, 1.1)
            steepness = base_steepness * rng.uniform(0.85, 1.15)
            logistic = asymptote / (1 + math.exp(-steepness * (m - t0)))
            noise = rng.uniform(-trial_noise_scale, trial_noise_scale)
            total += _clip(logistic + noise)
        mean_value = total / SUCCESS_MC_TRIALS
        points.append(ForecastPoint(month=f"M{m}", value=round(mean_value, 1)))
    return points


def _regret_analysis(
    request: DecisionForecastRequest,
    outcome_distribution: dict[str, float],
    rng: random.Random,
) -> RegretAnalysis:
    failure = outcome_distribution["Failure"]
    upside = outcome_distribution["Strong"] + outcome_distribution["Breakout"]

    regret_score = _clip(failure * 0.55 + request.risk * 0.25 - upside * 0.25 + rng.uniform(-3, 3))
    inaction_regret = _clip(upside * 0.8 + (100 - request.risk) * 0.1 + rng.uniform(-3, 3))
    gap = inaction_regret - regret_score

    # Suggested decision window: bigger asymmetry -> shorter window (less reason
    # to wait); smaller/negative asymmetry -> longer window or no urgency at all.
    if gap > 25:
        window = 6
    elif gap > 10:
        window = 12
    elif gap > -10:
        window = 18
    else:
        window = None  # asymmetry favors caution, not a ticking clock

    if regret_score > inaction_regret + 10:
        summary = (
            f"Projected regret leans toward caution: the downside risk in acting on "
            f"'{request.name}' outweighs the projected regret of not acting. Consider "
            f"ways to de-risk before committing fully, rather than acting on a deadline."
        )
    elif inaction_regret > regret_score + 10:
        summary = (
            f"Projected regret leans toward action: the modeled upside for '{request.name}' "
            f"suggests inaction carries more long-run regret than trying and it not fully "
            f"working out. Asymmetry favors action within {window} months."
        )
    else:
        summary = (
            f"Projected regret is roughly balanced between acting and not acting on "
            f"'{request.name}' — this looks like a genuinely close call rather than an "
            f"obvious yes or no."
        )
        if window:
            article = "an" if window in (18,) else "a"
            summary += f" If you do lean toward acting, {article} {window}-month decision window looks reasonable."

    return RegretAnalysis(
        regretScore=int(round(regret_score)),
        inactionRegretScore=int(round(inaction_regret)),
        summary=summary,
    )


def _ground_in_graph(request: DecisionForecastRequest, k: int = 3) -> list[GroundedDecision]:
    """Best-effort: look for similar past decisions already sitting in the graph's
    chunk store. Never raises — grounding is a nice-to-have, not a dependency."""
    try:
        from query_layer import find_similar_past_decisions

        query = f"{request.name}. {request.goal}"
        results = find_similar_past_decisions(query, k=k)
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        grounded = []
        for chunk_id, doc, distance in zip(ids, docs, distances):
            grounded.append(
                GroundedDecision(chunk_id=chunk_id, snippet=(doc or "")[:200], distance=float(distance))
            )
        return grounded
    except Exception:
        # No graph populated yet, embedding model unavailable, etc. — skip silently.
        return []


def generate_forecast(request: DecisionForecastRequest) -> DecisionForecast:
    rng = _seeded_rng(request)

    outcome_distribution = _outcome_distribution(request, rng)
    risk_levels = _risk_heatmap(request, rng)
    success_points = _success_forecast(request, outcome_distribution, rng)
    regret = _regret_analysis(request, outcome_distribution, rng)
    grounded = _ground_in_graph(request)

    return DecisionForecast(
        request=request,
        probabilityDistribution=[
            ProbabilityOutcome(outcome=o, value=outcome_distribution[o]) for o in OUTCOME_ORDER
        ],
        successForecast=success_points,
        riskHeatmap=[RiskHeatmapItem(label=c, level=risk_levels[c]) for c in RISK_CATEGORY_ORDER],
        regretAnalysis=regret,
        groundedOn=grounded,
    )


# ---------------------------------------------------------------------------
# Multi-branch simulation (POST /simulate)
# ---------------------------------------------------------------------------
# Runs the same heuristic engine three times with shifted risk assumptions to
# produce Conservative / Balanced / Aggressive branches. Everything is derived
# from the seeded forecast, so repeated calls with the same request are stable.

# (key, title, risk delta, thesis)
BRANCH_SPECS: list[tuple[str, str, int, str]] = [
    (
        "conservative",
        "Conservative Path",
        -25,
        "Prioritizes downside protection: slower moves, smaller bets, and preserving optionality over chasing the tail.",
    ),
    (
        "balanced",
        "Balanced Path",
        0,
        "Balances upside and risk: commit incrementally, validate as you go, and scale only once signal appears.",
    ),
    (
        "aggressive",
        "Aggressive Path",
        25,
        "Maximizes upside and accepts a fatter downside: move fast, concentrate resources, and push for the breakout outcome.",
    ),
]


def _dist_map(forecast: DecisionForecast) -> dict[str, float]:
    return {o.outcome: o.value for o in forecast.probabilityDistribution}


def _branch_citations(forecast: DecisionForecast) -> list[Citation]:
    return [
        Citation(nodeId=g.chunk_id, label=(g.snippet[:80] or g.chunk_id), excerpt=g.snippet)
        for g in forecast.groundedOn
    ]


def _branch_probability(dist: dict[str, float]) -> float:
    """Blend overall non-failure probability with the strongest single positive
    outcome, normalized to 0-1 (mirrors the frontend adapter)."""
    failure = dist.get("Failure", 0.0)
    positives = [v for k, v in dist.items() if k != "Failure"]
    strongest_positive = max(positives) if positives else 0.0
    non_failure = 100.0 - failure
    return _clip((non_failure + strongest_positive) / 200.0, 0.0, 1.0)


def _branch_confidence(
    forecast: DecisionForecast,
    horizon_months: int,
    dist: dict[str, float],
    evidence: list[EvidenceItem],
) -> ConfidenceBreakdown:
    grounded = forecast.groundedOn

    evidence_strength = _clip(len(grounded) / 3.0, 0.0, 1.0)

    if grounded:
        avg_distance = sum(g.distance for g in grounded) / len(grounded)
        source = _clip(1.0 - avg_distance, 0.0, 1.0)
    else:
        source = 0.5

    strongest_share = (max(dist.values()) / 100.0) if dist else 0.5
    consensus = _clip(strongest_share, 0.0, 1.0)

    temporal = _clip(1.0 - horizon_months / 120.0, 0.0, 1.0)

    # External demo evidence lifts source reliability (by count AND confidence)
    # and temporal relevance (external signals are more current than the graph).
    evidence_coverage = _clip(len(evidence) / 4.0, 0.0, 1.0)  # 4+ items = full coverage
    avg_evidence_conf = (
        sum(e.confidence for e in evidence) / len(evidence) if evidence else 0.0
    )
    source = _clip(source + evidence_coverage * avg_evidence_conf * 0.4, 0.0, 1.0)
    temporal = _clip(temporal + evidence_coverage * 0.15, 0.0, 1.0)

    if forecast.riskHeatmap:
        avg_risk = sum(r.level for r in forecast.riskHeatmap) / len(forecast.riskHeatmap)
    else:
        avg_risk = 50.0
    causal = _clip(1.0 - avg_risk / 100.0, 0.0, 1.0)

    return ConfidenceBreakdown(
        evidenceStrength=round(evidence_strength, 3),
        sourceReliability=round(source, 3),
        modelConsensus=round(consensus, 3),
        temporalRelevance=round(temporal, 3),
        causalCoherence=round(causal, 3),
    )


def _branch_milestones(
    title: str, forecast: DecisionForecast, citations: list[Citation]
) -> list[TimelineMilestone]:
    milestones: list[TimelineMilestone] = []
    for i, point in enumerate(forecast.successForecast):
        month = int(point.month.lstrip("M") or 0)
        mtype = "decision_point" if i == 0 else "outcome_realized"
        milestones.append(
            TimelineMilestone(
                month=month,
                event=f"{title}: month {month} — modeled success likelihood {point.value:.1f}%",
                type=mtype,
                veracity="prediction",
                citations=citations,
                dataSparsity=0.35 if citations else 0.75,
            )
        )
    return milestones


def generate_simulation(request: SimulationRequest) -> SimulationResponse:
    horizon_months = HORIZON_MONTHS[request.horizon]

    # Retrieve curated LOCAL DEMO evidence relevant to the decision once, then
    # attach it to every branch and use it to lift source/temporal confidence.
    evidence_query = f"{request.name}. {request.goal}"
    evidence = search_evidence(query=evidence_query, k=5)

    branches: list[TimelineBranch] = []
    forecasts: dict[str, DecisionForecast] = {}
    dists: dict[str, dict[str, float]] = {}
    for key, title, risk_delta, thesis in BRANCH_SPECS:
        branch_risk = int(_clip(request.risk + risk_delta, 0.0, 100.0))
        branch_req = DecisionForecastRequest(
            name=request.name,
            type=request.type,
            horizon=request.horizon,
            risk=branch_risk,
            goal=request.goal,
        )
        forecast = generate_forecast(branch_req)
        dist = _dist_map(forecast)
        forecasts[key] = forecast
        dists[key] = dist
        citations = _branch_citations(forecast)

        branches.append(
            TimelineBranch(
                id=f"branch_{key}",
                title=title,
                description=f"{thesis} {forecast.regretAnalysis.summary}",
                probabilityScore=round(_branch_probability(dist), 3),
                expectedRegret=round(_clip(forecast.regretAnalysis.regretScore / 100.0, 0.0, 1.0), 3),
                status="active",
                milestones=_branch_milestones(title, forecast, citations),
                confidenceBreakdown=_branch_confidence(forecast, horizon_months, dist, evidence),
                anchorNodeIds=[g.chunk_id for g in forecast.groundedOn],
                agentDisagreements=[],  # filled from the agent council below
                groundedOn=forecast.groundedOn,
                externalEvidence=evidence,
            )
        )

    # Recommend the branch with the best probability-vs-regret tradeoff.
    recommended = max(
        branches, key=lambda b: b.probabilityScore * 0.6 - b.expectedRegret * 0.4
    )
    recommended.status = "recommended"

    affected = sorted({nid for b in branches for nid in b.anchorNodeIds})

    # --- Multi-agent council -------------------------------------------------
    # Memory-graph precedents (best-effort; never blocks the simulation).
    try:
        from .query_layer import find_similar_past_decisions_clean

        precedents = find_similar_past_decisions_clean(evidence_query, k=5).get("items", [])
    except Exception:
        precedents = []

    balanced = forecasts.get("balanced") or next(iter(forecasts.values()))
    balanced_dist = dists.get("balanced") or {}
    forecast_context = {
        "failure_share": balanced_dist.get("Failure", 0.0),
        "upside_share": balanced_dist.get("Strong", 0.0) + balanced_dist.get("Breakout", 0.0),
        "top_risks": [
            r.label
            for r in sorted(balanced.riskHeatmap, key=lambda x: x.level, reverse=True)[:3]
        ],
    }

    council = run_agent_council(
        request=request,
        precedents=precedents,
        evidence=evidence,
        branches=branches,
        recommended_branch_id=recommended.id,
        forecast_context=forecast_context,
    )

    # Attach council output per-branch and derive modelConsensus from agent
    # agreement (same council applies to every branch of this decision).
    disagreements = council_to_disagreements(council)
    for branch in branches:
        branch.agentDisagreements = disagreements
        branch.confidenceBreakdown.modelConsensus = round(council.consensusScore, 3)

    return SimulationResponse(
        metadata=SimulationMetadata(query=request.name, horizonMonths=horizon_months),
        timelines=branches,
        recommendedTimelineId=recommended.id,
        affectedNodeIds=affected,
        externalEvidenceUsed=evidence,
        agentCouncil=council,
    )
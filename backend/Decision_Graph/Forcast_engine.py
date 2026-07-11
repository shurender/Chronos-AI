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
import uuid
from datetime import datetime, timezone

from backend.Agents.agent_council import council_to_disagreements, run_agent_council
from backend.External_Evidence.evidence_schema import EvidenceItem
from backend.External_Evidence.evidence_service import active_provider_name, search_evidence
from backend.simulation_schema import Assumption, DataCoverage, DecisionOption
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
        from .query_layer import find_similar_past_decisions_clean

        query = f"{request.name}. {request.goal}"
        items = find_similar_past_decisions_clean(query, k=k).get("items", [])
        grounded = []
        for item in items:
            grounded.append(
                GroundedDecision(
                    chunk_id=item.get("chunk_id"),
                    snippet=(item.get("snippet") or "")[:200],
                    distance=float(item.get("distance", 1.0)),
                    source_type=item.get("source_type"),
                    source_name=item.get("source_name"),
                    source_url=item.get("source_url"),
                    timestamp=item.get("timestamp"),
                )
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
        Citation(
            nodeId=g.chunk_id,
            label=(g.source_name or g.snippet[:80] or g.chunk_id),
            excerpt=g.snippet,
            url=g.source_url,
            source_type=g.source_type,
            source_name=g.source_name,
            source_url=g.source_url,
            timestamp=g.timestamp,
        )
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


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _evidence_is_stale(item: EvidenceItem) -> bool:
    dt = _parse_dt(item.published_at or item.retrieved_at)
    if not dt:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days > 365


def _data_coverage(
    precedents: list[dict],
    evidence: list[EvidenceItem],
    twin,
    intake,
) -> DataCoverage:
    graph_nodes = 0
    connector_ids: set[str] = set()
    uploaded_sources: set[str] = set()
    try:
        from backend.storage import G

        graph_nodes = G.number_of_nodes()
        for _, data in G.nodes(data=True):
            provider = data.get("connector_provider") or data.get("source_type")
            auth = data.get("source_auth")
            if provider in {"github", "slack", "notion"} or auth == "authenticated":
                connector_ids.add(str(data.get("connector_source_id") or provider))
            if provider in {"upload", "uploaded_file"} or auth == "uploaded":
                uploaded_sources.add(str(data.get("connector_source_id") or data.get("source_name") or "upload"))
    except Exception:
        graph_nodes = 0

    for p in precedents:
        provider = p.get("connector_provider") or p.get("source_type")
        if provider in {"github", "slack", "notion"}:
            connector_ids.add(str(p.get("connector_source_id") or provider))
        if provider in {"upload", "uploaded_file"}:
            uploaded_sources.add(str(p.get("connector_source_id") or provider))

    live_evidence = sum(1 for e in evidence if e.is_live_source)
    demo_evidence = sum(1 for e in evidence if e.is_demo_source)
    uploaded_evidence = sum(1 for e in evidence if e.source_kind == "uploaded")
    digital_twin_completeness = (
        float(twin.confidenceBreakdown.overallConfidence) if twin else 0.0
    )
    intake_completeness = float(intake.completenessScore) if intake else 0.0
    relevant_precedents = len(precedents)
    connector_count = len(connector_ids)
    uploaded_count = len(uploaded_sources) + uploaded_evidence

    graph_score = _clip(graph_nodes / 50.0, 0.0, 1.0)
    precedent_score = _clip(relevant_precedents / 5.0, 0.0, 1.0)
    evidence_score = _clip((live_evidence + uploaded_evidence * 0.8 + demo_evidence * 0.25) / 5.0, 0.0, 1.0)
    source_score = _clip((connector_count + uploaded_count * 0.7) / 3.0, 0.0, 1.0)
    overall = _clip(
        graph_score * 0.2
        + precedent_score * 0.2
        + evidence_score * 0.2
        + source_score * 0.2
        + digital_twin_completeness * 0.1
        + intake_completeness * 0.1,
        0.0,
        1.0,
    )

    gaps: list[str] = []
    if connector_count == 0 and uploaded_count == 0:
        gaps.append("No authenticated connector or uploaded workspace data is available.")
    if relevant_precedents == 0:
        gaps.append("No similar past decisions were found in the memory graph.")
    if live_evidence == 0:
        gaps.append("No live external evidence was available for this simulation.")
    if demo_evidence and live_evidence == 0 and connector_count == 0:
        gaps.append("Demo evidence is being used and is weighted lower than live/user data.")
    if digital_twin_completeness < 0.4:
        gaps.append("Digital twin profile is sparse.")
    if intake_completeness < 0.6:
        gaps.append("Decision intake is missing important context.")

    return DataCoverage(
        graphNodes=graph_nodes,
        relevantPrecedents=relevant_precedents,
        liveEvidence=live_evidence,
        demoEvidence=demo_evidence,
        connectorSources=connector_count,
        uploadedSources=uploaded_count,
        digitalTwinCompleteness=round(_clip(digital_twin_completeness, 0.0, 1.0), 3),
        intakeCompleteness=round(_clip(intake_completeness, 0.0, 1.0), 3),
        overallCoverage=round(overall, 3),
        gaps=gaps,
    )


def _branch_confidence(
    forecast: DecisionForecast,
    horizon_months: int,
    dist: dict[str, float],
    evidence: list[EvidenceItem],
    assumption_conf: float = 0.5,
    twin_completeness: float = 0.0,
    precedent_strength: float = 0.0,
    data_coverage: DataCoverage | None = None,
) -> ConfidenceBreakdown:
    grounded = forecast.groundedOn

    grounded_strength = _clip(len(grounded) / 3.0, 0.0, 1.0)

    if grounded:
        avg_distance = sum(g.distance for g in grounded) / len(grounded)
        source = _clip(1.0 - avg_distance, 0.0, 1.0)
    else:
        source = 0.5

    strongest_share = (max(dist.values()) / 100.0) if dist else 0.5
    consensus = _clip(strongest_share, 0.0, 1.0)

    temporal = _clip(1.0 - horizon_months / 120.0, 0.0, 1.0)

    # Evidence strength is weighted by provenance: live web and user/uploaded
    # data count more than demo evidence.
    weighted_evidence = sum(
        1.0 if e.is_live_source else 0.8 if e.source_kind == "uploaded" else 0.35 for e in evidence
    )
    evidence_coverage = _clip(weighted_evidence / 4.0, 0.0, 1.0)  # 4 weighted items = full coverage
    avg_evidence_conf = sum(e.confidence for e in evidence) / len(evidence) if evidence else 0.0
    live_count = data_coverage.liveEvidence if data_coverage else sum(1 for e in evidence if e.is_live_source)
    demo_count = data_coverage.demoEvidence if data_coverage else sum(1 for e in evidence if e.is_demo_source)
    real_connector_count = data_coverage.connectorSources if data_coverage else 0
    source = _clip(source + evidence_coverage * avg_evidence_conf * 0.35, 0.0, 1.0)
    source = _clip(source + precedent_strength * 0.15, 0.0, 1.0)  # historical precedent strength
    if live_count:
        source = _clip(source + min(live_count, 3) * 0.04, 0.0, 1.0)
        temporal = _clip(temporal + 0.12, 0.0, 1.0)
    if real_connector_count and precedent_strength:
        source = _clip(source + 0.08, 0.0, 1.0)
        grounded_strength = _clip(grounded_strength + 0.12, 0.0, 1.0)
    if demo_count and not live_count and real_connector_count == 0:
        source = _clip(source * 0.85, 0.0, 1.0)
    temporal = _clip(temporal + evidence_coverage * 0.08, 0.0, 1.0)
    stale_count = sum(1 for e in evidence if _evidence_is_stale(e))
    if stale_count:
        temporal = _clip(temporal - min(stale_count, 4) * 0.04, 0.0, 1.0)

    # Evidence strength blends graph grounding, evidence coverage, and how
    # confident this branch's own assumptions are.
    evidence_strength = _clip(
        0.4 * grounded_strength + 0.3 * evidence_coverage + 0.3 * assumption_conf, 0.0, 1.0
    )

    if forecast.riskHeatmap:
        avg_risk = sum(r.level for r in forecast.riskHeatmap) / len(forecast.riskHeatmap)
    else:
        avg_risk = 50.0
    causal = _clip(1.0 - avg_risk / 100.0, 0.0, 1.0)
    causal = _clip(causal + twin_completeness * 0.15, 0.0, 1.0)  # digital twin completeness
    if data_coverage and data_coverage.overallCoverage < 0.3:
        low_data_factor = _clip(0.72 + data_coverage.overallCoverage, 0.72, 1.0)
        evidence_strength *= low_data_factor
        source *= low_data_factor
        causal *= low_data_factor

    return ConfidenceBreakdown(
        evidenceStrength=round(evidence_strength, 3),
        sourceReliability=round(source, 3),
        modelConsensus=round(consensus, 3),
        temporalRelevance=round(temporal, 3),
        causalCoherence=round(causal, 3),
    )


# Semantic milestone scaffold (month, type, event template) — clipped to horizon.
_MILESTONE_TEMPLATES: list[tuple[int, str, str]] = [
    (0, "decision_point", "Commit to {title}: define the experiment and success criteria"),
    (3, "outcome_realized", "First validation signal — early demand/traction check"),
    (6, "project_phase", "Resource & market check — reassess runway and fit"),
    (12, "outcome_realized", "Outcome divergence — the trajectory becomes distinguishable"),
    (24, "external_event", "Scale-or-exit checkpoint"),
]


def _nearest_success(forecast: DecisionForecast, month: int) -> float | None:
    best: tuple[int, float] | None = None
    for p in forecast.successForecast:
        pm = int(p.month.lstrip("M") or 0)
        if best is None or abs(pm - month) < abs(best[0] - month):
            best = (pm, p.value)
    return best[1] if best else None


def _branch_milestones(
    title: str, forecast: DecisionForecast, citations: list[Citation], horizon_months: int
) -> list[TimelineMilestone]:
    milestones: list[TimelineMilestone] = []
    used_months: set[int] = set()

    def _add(month: int, mtype: str, event: str) -> None:
        val = _nearest_success(forecast, month)
        text = event if val is None else f"{event} (modeled success ~{val:.0f}%)"
        used_months.add(month)
        milestones.append(
            TimelineMilestone(
                month=month,
                event=text,
                type=mtype,
                veracity="prediction",
                citations=citations,
                dataSparsity=0.35 if citations else 0.75,
            )
        )

    for month, mtype, template in _MILESTONE_TEMPLATES:
        if month <= horizon_months:
            _add(month, mtype, template.format(title=title))

    if horizon_months not in used_months:
        _add(horizon_months, "outcome_realized", f"Horizon outcome — {title} result crystallizes")

    return milestones


def _effective_risk(request: SimulationRequest, option: DecisionOption) -> int:
    """Per-option risk: lower reversibility and more known risks -> higher risk."""
    risk = float(request.risk)
    if option.reversibility is not None:
        risk += (0.5 - option.reversibility) * 40.0
    risk += min(len(option.known_risks) * 5.0, 15.0)
    return int(_clip(risk, 0.0, 100.0))


def _build_assumptions(
    ident: str,
    option: DecisionOption | None,
    request: SimulationRequest,
    evidence: list[EvidenceItem],
    twin,
    dist: dict[str, float],
    horizon_months: int,
) -> list["Assumption"]:
    evidence_ids = [e.id for e in evidence[:3]]
    evidence_conf = (sum(e.confidence for e in evidence) / len(evidence)) if evidence else 0.4
    twin_conf = twin.confidenceBreakdown.overallConfidence if twin else 0.4

    resource_stmt = "Available resources (capital, team, time) are sufficient to execute this path."
    if option and option.upfront_cost:
        resource_stmt = (
            f"The upfront cost ({option.upfront_cost}) and available resources are sufficient to execute."
        )

    assumptions = [
        Assumption(
            id=f"asm_market_{ident}",
            statement=f"There is enough market demand to make '{request.name}' viable within {horizon_months} months.",
            type="market",
            confidence=round(_clip(0.3 + evidence_conf * 0.5, 0.0, 1.0), 3),
            evidenceIds=evidence_ids,
            riskIfWrong="Demand fails to materialize; the branch underperforms its modeled upside.",
        ),
        Assumption(
            id=f"asm_resource_{ident}",
            statement=resource_stmt,
            type="resource",
            confidence=round(_clip(0.3 + twin_conf * 0.5, 0.0, 1.0), 3),
            evidenceIds=[],
            riskIfWrong="Runway or capacity runs out before the path reaches an outcome.",
        ),
        Assumption(
            id=f"asm_timing_{ident}",
            statement=f"The {request.horizon} horizon is long enough for results to become distinguishable.",
            type="timing",
            confidence=round(_clip(1.0 - horizon_months / 150.0, 0.0, 1.0), 3),
            evidenceIds=[],
            riskIfWrong="Signal arrives later than modeled; early checkpoints mislead.",
        ),
    ]
    if twin and twin.execution_style.style != "insufficient data":
        assumptions.append(
            Assumption(
                id=f"asm_behavior_{ident}",
                statement=f"Execution follows the observed pattern: {twin.execution_style.style}.",
                type="behavior",
                confidence=round(_clip(0.3 + twin_conf * 0.4, 0.0, 1.0), 3),
                evidenceIds=twin.source_chunk_ids[:2],
                riskIfWrong="Execution discipline differs from history, changing follow-through.",
            )
        )
    return assumptions


def _risk_factors(forecast: DecisionForecast, option: DecisionOption | None) -> list[str]:
    top = [r.label for r in sorted(forecast.riskHeatmap, key=lambda x: x.level, reverse=True)[:3]]
    factors = [f"Elevated {r.lower()} risk" for r in top]
    if option:
        factors += [f"Known risk: {kr}" for kr in option.known_risks[:3]]
    return factors


def _upside_factors(dist: dict[str, float], option: DecisionOption | None) -> list[str]:
    upside = dist.get("Strong", 0.0) + dist.get("Breakout", 0.0)
    factors = [f"~{upside:.0f}% modeled chance of a strong/breakout outcome"]
    if option and option.expected_upside:
        factors.append(f"Stated upside: {option.expected_upside}")
    return factors


def _failure_modes(forecast: DecisionForecast, dist: dict[str, float]) -> list[str]:
    failure = dist.get("Failure", 0.0)
    top = [r.label for r in sorted(forecast.riskHeatmap, key=lambda x: x.level, reverse=True)[:2]]
    modes = [f"Runs out of runway before an outcome (~{failure:.0f}% modeled failure share)"]
    modes += [f"{r} pressure derails execution" for r in top]
    return modes


def _leading_indicators(request: SimulationRequest) -> list[str]:
    base = [
        "Early demand / engagement signal in the first 90 days",
        "Cost trajectory vs. plan",
        "Whether committed milestones are hit on time",
    ]
    if request.type == "Startup":
        base.append("Design-partner or pilot conversion rate")
    elif request.type == "Career":
        base.append("Skill/role market demand trend")
    return base


def _decision_checkpoints(horizon_months: int) -> list[str]:
    points = [m for m in (3, 6, 12, 24) if m <= horizon_months]
    if horizon_months not in points:
        points.append(horizon_months)
    return [f"Month {m}: reassess and decide continue / adjust / exit" for m in points]


def _twin_factors(twin) -> list[str]:
    if not twin:
        return []
    factors = [
        f"Subject type: {twin.subject_type}",
        f"Risk profile: {twin.risk_profile.level}",
        f"Execution style: {twin.execution_style.style}",
    ]
    factors += [p.label for p in twin.behavioral_patterns[:2]]
    return factors


def _branch_specs(request: SimulationRequest) -> list[tuple[str, str, str, DecisionOption | None, int, str]]:
    """Return (key, title, thesis, option, branch_risk, seed_name) per branch.

    2+ options -> one branch per option (+ a hybrid branch when exactly two).
    Otherwise -> the Conservative/Balanced/Aggressive fallback, seeded exactly as
    before so results are unchanged for the no-options path."""
    options = request.options
    if len(options) >= 2:
        specs: list[tuple[str, str, str, DecisionOption | None, int, str]] = []
        for opt in options:
            thesis = opt.description or f"Pursue this option: {opt.label}."
            specs.append(
                (opt.id, opt.label, thesis, opt, _effective_risk(request, opt), f"{request.name} — Option: {opt.label}")
            )
        if len(options) == 2:
            specs.append(
                (
                    "hybrid",
                    "Hybrid / Phased",
                    "Sequence the two options: validate the cheaper / more reversible one first, then commit to the winner.",
                    None,
                    int(request.risk),
                    f"{request.name} — Hybrid path",
                )
            )
        return specs

    return [
        (key, title, thesis, None, int(_clip(request.risk + delta, 0.0, 100.0)), request.name)
        for key, title, delta, thesis in BRANCH_SPECS
    ]


def _record_provenance(
    branches: list[TimelineBranch], recommended_id: str, simulation_id: str, evidence: list[EvidenceItem]
) -> dict:
    """Create ClaimRecords for each branch's assumptions / milestones / risk, plus
    one recommendation claim. Sets branch.claimIds and returns a summary dict.
    Best-effort: any failure leaves claimIds empty rather than breaking /simulate."""
    from backend.Provenance.provenance_schema import ClaimRecord
    from backend.Provenance.provenance_service import create_claim

    by_type: dict[str, int] = {}
    total = 0
    evidence_by_id = {item.id: item for item in evidence}

    def _emit(branch: TimelineBranch, text: str, ctype: str, conf: float, evidence_ids, reason):
        nonlocal total
        rec = create_claim(
            ClaimRecord(
                claim_text=text,
                claim_type=ctype,
                created_by="simulation",
                source_ids=list(branch.anchorNodeIds),
                evidence_ids=list(evidence_ids),
                source_links=[
                    {
                        "source_id": evidence_by_id[eid].id,
                        "source_type": evidence_by_id[eid].source_kind,
                        "source_name": evidence_by_id[eid].source_name,
                        "source_url": evidence_by_id[eid].source_url,
                        "timestamp": evidence_by_id[eid].published_at or evidence_by_id[eid].retrieved_at,
                        "excerpt": evidence_by_id[eid].summary,
                    }
                    for eid in evidence_ids
                    if eid in evidence_by_id
                ],
                graph_node_ids=list(branch.anchorNodeIds),
                confidence=round(float(conf), 3),
                uncertainty_reason=reason,
                timeline_id=branch.id,
                simulation_id=simulation_id,
            )
        )
        branch.claimIds.append(rec.claim_id)
        by_type[ctype] = by_type.get(ctype, 0) + 1
        total += 1

    for branch in branches:
        for a in branch.assumptions:
            _emit(branch, a.statement, "inference", a.confidence, a.evidenceIds, a.riskIfWrong)
        if branch.milestones:
            _emit(
                branch,
                "Projected trajectory: " + "; ".join(m.event for m in branch.milestones[:6]),
                "prediction",
                branch.probabilityScore,
                branch.evidenceUsed[:5],
                "Heuristic projection, not an observed outcome.",
            )
        if branch.riskFactors or branch.failureModes:
            _emit(
                branch,
                "Risk factors: " + "; ".join(branch.riskFactors)
                + (". Failure modes: " + "; ".join(branch.failureModes) if branch.failureModes else ""),
                "inference",
                branch.expectedRegret,
                [],
                "Heuristic risk estimate from the forecast engine.",
            )
        if branch.id == recommended_id:
            _emit(
                branch,
                f"Recommended path: {branch.title} "
                f"(probability {branch.probabilityScore * 100:.0f}%, regret {branch.expectedRegret * 100:.0f}%).",
                "recommendation",
                branch.probabilityScore,
                branch.evidenceUsed[:5],
                "Best probability-vs-regret tradeoff among the branches.",
            )

    return {"simulationId": simulation_id, "totalClaims": total, "claimsByType": by_type}


def _agent_mode() -> str:
    """Read AGENT_MODE at call time so it can be overridden per environment/test."""
    from backend import config

    return config.AGENT_MODE


def generate_simulation(
    request: SimulationRequest, evidence_override: list[EvidenceItem] | None = None
) -> SimulationResponse:
    horizon_months = HORIZON_MONTHS[request.horizon]
    simulation_id = str(uuid.uuid4())

    # Retrieve evidence once (via the active provider). The exact list is
    # snapshotted into the response so it can't be silently changed later.
    # Replay can pass evidence_override to reuse a stored snapshot verbatim.
    evidence_query = f"{request.name}. {request.goal}"
    if evidence_override is not None:
        evidence = evidence_override
        evidence_provider = "replay:original_evidence"
    else:
        evidence = search_evidence(query=evidence_query, k=5)
        evidence_provider = active_provider_name()
    option_labels = [o.label for o in request.options]

    # Memory-graph precedents (best-effort; never blocks the simulation).
    try:
        from .query_layer import find_similar_past_decisions_clean

        precedents = find_similar_past_decisions_clean(evidence_query, k=5).get("items", [])
    except Exception:
        precedents = []
    precedent_strength = _clip(len(precedents) / 5.0, 0.0, 1.0)

    # Digital Twin Constructor — best-effort; never blocks the simulation.
    twin = None
    try:
        from backend.Digital_Twin.digital_twin_schema import DigitalTwinBuildRequest
        from backend.Digital_Twin.digital_twin_service import build_digital_twin

        twin = build_digital_twin(
            DigitalTwinBuildRequest(
                decisionQuestion=request.name,
                decisionType=request.type,
                goal=request.goal,
                constraints=request.constraints,
                geography=request.geography,
                options=option_labels,
            )
        )
    except Exception:
        twin = None
    twin_completeness = twin.confidenceBreakdown.overallConfidence if twin else 0.0
    twin_factors = _twin_factors(twin)

    # Clarifying Intake analysis - detect missing decision context before branch
    # scoring so low-completeness runs are visibly less confident.
    intake = None
    try:
        from backend.Intake.intake_schema import IntakeAnalyzeRequest
        from backend.Intake.intake_service import analyze_intake

        intake = analyze_intake(
            IntakeAnalyzeRequest(
                decisionQuestion=request.name,
                decisionType=request.type,
                horizon=request.horizon,
                risk=request.risk,
                goal=request.goal,
                constraints=request.constraints,
                geography=request.geography,
                options=option_labels,
                digitalTwinProfile=(twin.model_dump(mode="json") if twin else None),
                evidenceCount=len(evidence),
                precedentCount=len(precedents),
            )
        )
    except Exception:
        intake = None

    data_coverage = _data_coverage(precedents, evidence, twin, intake)

    # Build one branch per spec (option-aware; see _branch_specs).
    branches: list[TimelineBranch] = []
    forecasts: dict[str, DecisionForecast] = {}
    dists: dict[str, dict[str, float]] = {}
    for key, title, thesis, option, branch_risk, seed_name in _branch_specs(request):
        branch_req = DecisionForecastRequest(
            name=seed_name,  # option label folded into the seed -> distinct forecast per option
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

        assumptions = _build_assumptions(key, option, request, evidence, twin, dist, horizon_months)
        assumption_conf = (
            sum(a.confidence for a in assumptions) / len(assumptions) if assumptions else 0.5
        )

        branches.append(
            TimelineBranch(
                id=f"branch_{key}",
                title=title,
                description=f"{thesis} {forecast.regretAnalysis.summary}",
                probabilityScore=round(_branch_probability(dist), 3),
                expectedRegret=round(_clip(forecast.regretAnalysis.regretScore / 100.0, 0.0, 1.0), 3),
                status="active",
                milestones=_branch_milestones(title, forecast, citations, horizon_months),
                confidenceBreakdown=_branch_confidence(
                    forecast,
                    horizon_months,
                    dist,
                    evidence,
                    assumption_conf,
                    twin_completeness,
                    precedent_strength,
                    data_coverage,
                ),
                anchorNodeIds=[g.chunk_id for g in forecast.groundedOn],
                agentDisagreements=[],  # filled from the agent council below
                groundedOn=forecast.groundedOn,
                externalEvidence=evidence,
                optionId=option.id if option else None,
                assumptions=assumptions,
                evidenceUsed=[e.id for e in evidence],
                digitalTwinFactors=twin_factors,
                riskFactors=_risk_factors(forecast, option),
                upsideFactors=_upside_factors(dist, option),
                failureModes=_failure_modes(forecast, dist),
                leadingIndicators=_leading_indicators(request),
                decisionCheckpoints=_decision_checkpoints(horizon_months),
            )
        )

    # Recommend the branch with the best probability-vs-regret tradeoff.
    recommended = max(
        branches, key=lambda b: b.probabilityScore * 0.6 - b.expectedRegret * 0.4
    )
    recommended.status = "recommended"

    affected = sorted({nid for b in branches for nid in b.anchorNodeIds})

    # --- Multi-agent council -------------------------------------------------
    representative = forecasts.get("balanced") or next(iter(forecasts.values()))
    representative_dist = dists.get("balanced") or next(iter(dists.values()))
    forecast_context = {
        "failure_share": representative_dist.get("Failure", 0.0),
        "upside_share": representative_dist.get("Strong", 0.0) + representative_dist.get("Breakout", 0.0),
        "top_risks": [
            r.label
            for r in sorted(representative.riskHeatmap, key=lambda x: x.level, reverse=True)[:3]
        ],
    }

    # Clarifying Intake analysis — detect missing decision context. Never blocks
    # (decisionQuestion is always present here); low completeness -> confidence penalty.
    intake_missing = intake.missingFields if intake else None
    intake_low = bool(intake and intake.completenessScore < 0.6)

    council = run_agent_council(
        request=request,
        precedents=precedents,
        evidence=evidence,
        branches=branches,
        recommended_branch_id=recommended.id,
        forecast_context=forecast_context,
        twin=twin,
        intake_missing_fields=intake_missing,
        intake_low_completeness=intake_low,
        data_coverage=data_coverage.model_dump(),
        agent_mode=_agent_mode(),
    )

    # Safety: high-stakes decisions (Financial/Life) get conservative confidence
    # and a professional-advice warning; all decisions carry a disclaimer.
    from backend.Safety.policy import HIGH_STAKES_CONFIDENCE_FACTOR, build_safety_label

    safety = build_safety_label(request.type)
    stakes_factor = HIGH_STAKES_CONFIDENCE_FACTOR if safety.high_stakes else 1.0

    # Attach council output per-branch and derive modelConsensus from agent
    # agreement (same council applies to every branch of this decision).
    # Also apply the intake confidence penalty (missing context scales confidence
    # down, up to 50% at zero completeness) and the high-stakes factor.
    penalty_factor = (1.0 - (intake.confidencePenalty * 0.5 if intake else 0.0)) * stakes_factor
    disagreements = council_to_disagreements(council)
    for branch in branches:
        branch.agentDisagreements = disagreements
        cb = branch.confidenceBreakdown
        cb.modelConsensus = council.consensusScore
        cb.evidenceStrength = round(cb.evidenceStrength * penalty_factor, 3)
        cb.sourceReliability = round(cb.sourceReliability * penalty_factor, 3)
        cb.modelConsensus = round(cb.modelConsensus * penalty_factor, 3)
        cb.temporalRelevance = round(cb.temporalRelevance * penalty_factor, 3)
        cb.causalCoherence = round(cb.causalCoherence * penalty_factor, 3)

    # Provenance: record traceable claims for every branch. Best-effort.
    provenance_summary = None
    try:
        provenance_summary = _record_provenance(branches, recommended.id, simulation_id, evidence)
    except Exception:
        provenance_summary = None

    return SimulationResponse(
        metadata=SimulationMetadata(query=request.name, horizonMonths=horizon_months),
        timelines=branches,
        recommendedTimelineId=recommended.id,
        affectedNodeIds=affected,
        externalEvidenceUsed=evidence,
        dataCoverage=data_coverage,
        isDemoEvidence=all(e.is_demo_source for e in evidence) if evidence else True,
        evidenceProvider=evidence_provider,
        agentCouncil=council,
        digitalTwinProfileId=twin.profile_id if twin else None,
        digitalTwinSummary=twin.decision_history_summary if twin else None,
        intakeAnalysis=intake,
        simulationId=simulation_id,
        provenanceSummary=provenance_summary,
        safety=safety,
    )

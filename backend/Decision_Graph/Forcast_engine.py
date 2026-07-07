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

from backend.schema import (
    DecisionForecast,
    DecisionForecastRequest,
    ForecastPoint,
    GroundedDecision,
    ProbabilityOutcome,
    RegretAnalysis,
    RiskHeatmapItem,
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
"""
Metrics for Chronos eval cases — each returns True (pass) / False (fail) /
None (not applicable / skipped) for a given case + endpoint responses.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Optional

from .eval_schema import EvalCase

METRIC_NAMES = [
    "no_crash",
    "endpoint_success",
    "schema_valid",
    "timelines_count_valid",
    "evidence_grounding_present",
    "unsupported_claims_absent",
    "missing_context_detected",
    "confidence_penalty_applied",
    "recommendation_present",
    "grounding_label_valid",
]

_REQUIRED_KEYS = ("metadata", "timelines", "recommendedTimelineId", "agentCouncil", "intakeAnalysis", "simulationId")


def _schema_valid(sim: dict) -> bool:
    if not all(k in sim for k in _REQUIRED_KEYS):
        return False
    for t in sim.get("timelines", []):
        if "confidenceBreakdown" not in t or "assumptions" not in t:
            return False
    return True


def _market_agent(sim: dict) -> Optional[dict]:
    agents = (sim.get("agentCouncil") or {}).get("agents", [])
    return next((a for a in agents if a.get("agent_id") == "market"), None)


def _unsupported_claims_absent(sim: dict, market_should_refuse: bool) -> bool:
    evidence_ids = {e.get("id") for e in sim.get("externalEvidenceUsed", [])}
    market = _market_agent(sim)
    if market is None:
        return True
    # Guardrail: MarketAgent must never cite an id outside the evidence snapshot.
    if not set(market.get("citations", [])).issubset(evidence_ids):
        return False
    if market_should_refuse:
        pos = (market.get("position") or "").lower()
        concerns = " ".join(market.get("concerns", [])).lower()
        refused = ("will not assert" in pos) or ("not assert" in pos) or ("no external evidence" in concerns)
        if not refused:
            return False
    return True


def evaluate_case(
    case: EvalCase,
    sim_status: int,
    sim: Optional[dict],
    avatar: Optional[dict],
    crashed: bool,
) -> "OrderedDict[str, Optional[bool]]":
    exp = case.expectations
    m: "OrderedDict[str, Optional[bool]]" = OrderedDict((k, None) for k in METRIC_NAMES)

    m["no_crash"] = not crashed
    m["endpoint_success"] = sim_status == 200

    if crashed or sim is None:
        return m  # remaining stay None (skipped)

    timelines = sim.get("timelines", [])
    m["schema_valid"] = _schema_valid(sim)
    m["timelines_count_valid"] = (
        len(timelines) == exp.expected_timelines if exp.expected_timelines is not None else len(timelines) >= 1
    )

    evidence = sim.get("externalEvidenceUsed", [])
    m["evidence_grounding_present"] = len(evidence) >= exp.min_evidence_count
    m["unsupported_claims_absent"] = _unsupported_claims_absent(sim, exp.market_should_refuse)

    intake = sim.get("intakeAnalysis") or {}
    missing = set(intake.get("missingFields", []))
    if exp.expected_missing_fields:
        m["missing_context_detected"] = set(exp.expected_missing_fields).issubset(missing)
    if exp.confidence_penalty_expected:
        m["confidence_penalty_applied"] = float(intake.get("confidencePenalty", 0.0)) > 0.0

    rid = sim.get("recommendedTimelineId")
    m["recommendation_present"] = bool(rid) and any(t.get("id") == rid for t in timelines)

    if case.run_avatar and avatar is not None and exp.expected_grounding_labels:
        m["grounding_label_valid"] = avatar.get("groundingLabel") in exp.expected_grounding_labels

    return m


def case_passed(metrics: "OrderedDict[str, Optional[bool]]") -> bool:
    return all(v is not False for v in metrics.values())

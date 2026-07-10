"""
Digital Twin Constructor — builds a deterministic-first structured profile of
the subject (individual/team/org) from the memory graph, historical
precedents, structured intake, and external evidence.

Deterministic by design: no LLM call is required for a profile to be built.
Every inferred item carries a citation; anything that couldn't be inferred is
listed under missing_information rather than silently omitted.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from backend import storage
from backend.logging_config import get_logger

from .digital_twin_schema import (
    DigitalTwinBuildRequest,
    DigitalTwinConfidenceBreakdown,
    DigitalTwinProfile,
    ExecutionStyle,
    ProfileItem,
    RiskProfile,
    TeamTopology,
)

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent
PROFILES_STORE_PATH = os.getenv("DIGITAL_TWIN_STORE_PATH", str(BASE_DIR / "profiles.json"))

_lock = threading.Lock()
_profiles: dict[str, dict] = {}
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    if os.path.exists(PROFILES_STORE_PATH):
        with open(PROFILES_STORE_PATH, "r", encoding="utf-8") as f:
            try:
                _profiles.update(json.load(f))
            except json.JSONDecodeError:
                pass
    _loaded = True


def _persist(profile: DigitalTwinProfile) -> None:
    _ensure_loaded()
    with _lock:
        _profiles[profile.profile_id] = json.loads(profile.model_dump_json())
        os.makedirs(os.path.dirname(PROFILES_STORE_PATH) or ".", exist_ok=True)
        with open(PROFILES_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(_profiles, f, indent=2, default=str)


def get_profile(profile_id: str) -> dict | None:
    _ensure_loaded()
    return _profiles.get(profile_id)


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _nodes_by_type(node_type: str) -> list[dict]:
    if not storage.G.number_of_nodes():
        return []
    return [d for _, d in storage.G.nodes(data=True) if d.get("node_type") == node_type]


def _subject_type_and_topology(person_nodes: list[dict]) -> tuple[str, TeamTopology | None]:
    n = len(person_nodes)
    if n <= 1:
        return "individual", None
    subject = "team" if n <= 5 else "org"
    roles = [p.get("label", "unknown") for p in person_nodes][:20]
    return subject, TeamTopology(size_estimate=n, roles=roles)


def _infer_risk_profile(outcome_nodes: list[dict], precedents: list[dict]) -> RiskProfile:
    if not outcome_nodes and not precedents:
        return RiskProfile(
            level="unknown",
            score=0.0,
            rationale=["No outcome nodes or historical precedents to infer risk tendency from."],
        )
    avg_conf = (
        sum(n.get("confidence", 0.5) for n in outcome_nodes) / len(outcome_nodes)
        if outcome_nodes
        else 0.5
    )
    # Sparse/low-confidence outcome history reads as higher unresolved risk.
    score = _clip01(1.0 - avg_conf)
    level = "low" if score < 0.35 else "moderate" if score < 0.65 else "high"
    rationale = [
        f"Derived from {len(outcome_nodes)} outcome node(s) with average confidence {avg_conf:.2f}.",
    ]
    if precedents:
        rationale.append(f"{len(precedents)} similar past decision(s) found in memory graph.")
    return RiskProfile(level=level, score=round(score, 3), rationale=rationale)


def _infer_execution_style(project_nodes: list[dict], outcome_nodes: list[dict]) -> ExecutionStyle:
    if not project_nodes and not outcome_nodes:
        return ExecutionStyle(
            style="insufficient data",
            rationale=["No project or outcome nodes in the memory graph to infer execution style from."],
        )
    ratio = len(outcome_nodes) / max(len(project_nodes), 1)
    if ratio >= 0.75:
        style = "consistently ships and reaches outcomes"
    elif ratio >= 0.3:
        style = "mixed follow-through — some projects reach outcomes, others stall"
    else:
        style = "many projects started, few tracked outcomes"
    return ExecutionStyle(
        style=style,
        rationale=[f"{len(project_nodes)} project node(s), {len(outcome_nodes)} outcome node(s) in graph."],
    )


def _infer_behavioral_patterns(decision_nodes: list[dict], precedents: list[dict]) -> list[ProfileItem]:
    patterns: list[ProfileItem] = []
    if decision_nodes:
        fact_count = sum(1 for n in decision_nodes if n.get("evidence_type") == "fact")
        if fact_count:
            patterns.append(
                ProfileItem(
                    label=f"{fact_count}/{len(decision_nodes)} past decisions are directly evidenced (not inferred)",
                    confidence=_clip01(fact_count / len(decision_nodes)),
                    citations=[
                        cid
                        for n in decision_nodes
                        if n.get("evidence_type") == "fact"
                        for cid in n.get("source_chunk_ids", [])
                    ][:5],
                )
            )
    if precedents:
        patterns.append(
            ProfileItem(
                label=f"{len(precedents)} similar past decision(s) exist — some repeat pattern likely",
                confidence=_clip01(len(precedents) / 5.0),
                citations=[p.get("chunk_id") for p in precedents[:5] if p.get("chunk_id")],
            )
        )
    return patterns


def _summarize_history(decision_nodes: list[dict], outcome_nodes: list[dict], precedents: list[dict]) -> str:
    if not decision_nodes and not outcome_nodes and not precedents:
        return "No decision history available in the memory graph or precedent search."
    parts = []
    if decision_nodes:
        parts.append(f"{len(decision_nodes)} past decision(s)")
    if outcome_nodes:
        parts.append(f"{len(outcome_nodes)} tracked outcome(s)")
    if precedents:
        parts.append(f"{len(precedents)} similar precedent(s) via search")
    return "Memory graph / precedent search found " + ", ".join(parts) + "."


def _detect_missing_information(
    request: DigitalTwinBuildRequest,
    skill_nodes: list[dict],
    outcome_nodes: list[dict],
    precedents: list[dict],
    evidence_items: list,
) -> list[str]:
    missing = []
    if not request.geography:
        missing.append("No geography/context provided.")
    if not any(k in (request.decisionQuestion or "").lower() for k in ("year", "month", "quarter", "week")):
        missing.append("No explicit time horizon in the decision context.")
    if not outcome_nodes:
        missing.append("No outcome data in memory graph — risk/execution inferences are not grounded in observed results.")
    if not precedents:
        missing.append("No historical precedents found for this decision.")
    if request.useEvidence and not evidence_items:
        missing.append("No external evidence found relevant to this decision.")
    elif not request.useEvidence:
        missing.append("External evidence lookup was disabled for this profile.")
    if len(skill_nodes) < 2:
        missing.append("Weak skill history: fewer than 2 skill signals found in memory graph.")
    if not storage.G.number_of_nodes():
        missing.append("Memory graph is empty — profile is based only on structured intake.")
    return missing


def _detect_contradictions(all_nodes: list[dict]) -> list[str]:
    """Cheap heuristic: same label appearing with meaningfully different
    confidence or a different evidence_type suggests conflicting evidence."""
    by_label: dict[str, list[dict]] = {}
    for n in all_nodes:
        by_label.setdefault((n.get("label") or "").strip().lower(), []).append(n)

    contradictions = []
    for label, nodes in by_label.items():
        if len(nodes) < 2 or not label:
            continue
        evidence_types = {n.get("evidence_type") for n in nodes}
        confidences = [n.get("confidence", 0.5) for n in nodes]
        if len(evidence_types) > 1 or (max(confidences) - min(confidences) > 0.3):
            contradictions.append(
                f"Conflicting signals for '{nodes[0].get('label')}': "
                f"evidence_types={sorted(evidence_types)}, confidence range "
                f"{min(confidences):.2f}-{max(confidences):.2f}."
            )
    return contradictions


def build_digital_twin(request: DigitalTwinBuildRequest) -> DigitalTwinProfile:
    skill_nodes = person_nodes = project_nodes = outcome_nodes = decision_nodes = []
    if request.useGraph:
        skill_nodes = _nodes_by_type("skill")
        person_nodes = _nodes_by_type("person")
        project_nodes = _nodes_by_type("project")
        outcome_nodes = _nodes_by_type("outcome")
        decision_nodes = _nodes_by_type("decision")

    precedents: list[dict] = []
    if request.useGraph and request.decisionQuestion:
        try:
            from backend.Decision_Graph.query_layer import find_similar_past_decisions_clean

            precedents = find_similar_past_decisions_clean(request.decisionQuestion, k=5).get("items", [])
        except Exception as exc:
            logger.warning("Digital twin precedent lookup failed: %s", exc)

    evidence_items = []
    if request.useEvidence:
        try:
            from backend.External_Evidence.evidence_service import search_evidence

            query = request.decisionQuestion or request.goal or ""
            evidence_items = search_evidence(query=query, k=5)
        except Exception as exc:
            logger.warning("Digital twin evidence lookup failed: %s", exc)

    inferred_skills = [
        ProfileItem(label=n.get("label", "unknown"), confidence=n.get("confidence", 0.5), citations=n.get("source_chunk_ids", []))
        for n in skill_nodes
    ]
    resources = [
        ProfileItem(label=n.get("label", "unknown"), confidence=n.get("confidence", 0.5), citations=n.get("source_chunk_ids", []))
        for n in outcome_nodes
    ]

    goals: list[ProfileItem] = []
    if request.goal:
        goals.append(ProfileItem(label=request.goal, confidence=1.0, citations=[]))
    goals += [
        ProfileItem(label=n.get("label", "unknown"), confidence=_clip01(n.get("confidence", 0.5) * 0.7), citations=n.get("source_chunk_ids", []))
        for n in decision_nodes
    ]

    constraints: list[ProfileItem] = []
    if request.constraints:
        constraints.append(ProfileItem(label=request.constraints, confidence=1.0, citations=[]))

    subject_type, team_topology = _subject_type_and_topology(person_nodes)

    all_nodes = skill_nodes + person_nodes + project_nodes + outcome_nodes + decision_nodes
    source_chunk_ids = sorted(
        {cid for n in all_nodes for cid in n.get("source_chunk_ids", [])}
        | {p.get("chunk_id") for p in precedents if p.get("chunk_id")}
    )
    external_evidence_ids = [e.id for e in evidence_items]

    intake_fields = [
        request.decisionQuestion,
        request.decisionType,
        request.goal,
        request.constraints,
        request.geography,
        request.options,
    ]
    intake_completeness = _clip01(sum(1 for f in intake_fields if f) / len(intake_fields))
    graph_coverage = _clip01(len(all_nodes) / 15.0)
    evidence_coverage = _clip01(len(evidence_items) / 5.0)
    overall = _clip01(0.4 * graph_coverage + 0.2 * evidence_coverage + 0.4 * intake_completeness)

    profile = DigitalTwinProfile(
        subject_type=subject_type,
        inferred_skills=inferred_skills,
        resources=resources,
        constraints=constraints,
        goals=goals,
        behavioral_patterns=_infer_behavioral_patterns(decision_nodes, precedents),
        decision_history_summary=_summarize_history(decision_nodes, outcome_nodes, precedents),
        risk_profile=_infer_risk_profile(outcome_nodes, precedents),
        execution_style=_infer_execution_style(project_nodes, outcome_nodes),
        team_topology=team_topology,
        missing_information=_detect_missing_information(request, skill_nodes, outcome_nodes, precedents, evidence_items),
        contradictions=_detect_contradictions(all_nodes),
        confidenceBreakdown=DigitalTwinConfidenceBreakdown(
            graphCoverage=round(graph_coverage, 3),
            evidenceCoverage=round(evidence_coverage, 3),
            intakeCompleteness=round(intake_completeness, 3),
            overallConfidence=round(overall, 3),
        ),
        source_chunk_ids=source_chunk_ids,
        external_evidence_ids=external_evidence_ids,
    )

    _persist(profile)
    return profile

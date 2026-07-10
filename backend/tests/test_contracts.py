"""
Backend API contract tests.

Freezes the public response shapes documented in docs/API_CONTRACT.md and
Frontend/src/api/contracts.ts, so an accidental field rename/removal fails loudly.

Two layers:
  1. model-field freeze — each Pydantic model must still expose its documented fields.
  2. live endpoint checks — responses re-validate against their model + carry the
     expected top-level fields.

Runs in deterministic/mock mode (no API keys). Both pytest-collectable
(`test_*` functions) and runnable standalone:

    python -m backend.tests.test_contracts
"""

from __future__ import annotations

import sys

# --- Frozen field sets (must remain a SUBSET of each model's fields) ----------
FROZEN_MODEL_FIELDS = {
    "SimulationRequest": {"name", "type", "horizon", "risk", "goal", "constraints", "geography", "options"},
    "SimulationResponse": {
        "metadata", "timelines", "recommendedTimelineId", "affectedNodeIds", "externalEvidenceUsed",
        "isDemoEvidence", "evidenceProvider", "agentCouncil", "digitalTwinProfileId", "digitalTwinSummary",
        "intakeAnalysis", "simulationId", "provenanceSummary", "safety", "methodology",
    },
    "TimelineBranch": {
        "id", "title", "description", "probabilityScore", "expectedRegret", "status", "milestones",
        "confidenceBreakdown", "anchorNodeIds", "agentDisagreements", "groundedOn", "externalEvidence",
        "optionId", "assumptions", "evidenceUsed", "digitalTwinFactors", "riskFactors", "upsideFactors",
        "failureModes", "leadingIndicators", "decisionCheckpoints", "claimIds",
    },
    "ConfidenceBreakdown": {
        "evidenceStrength", "sourceReliability", "modelConsensus", "temporalRelevance", "causalCoherence",
    },
    "EvidenceItem": {
        "id", "domain", "title", "summary", "source_name", "source_url", "published_at", "evidence_type",
        "confidence", "tags", "source_kind", "retrieved_at", "freshness_score", "source_reliability",
        "is_live_source", "is_demo_source",
    },
    "AgentCouncil": {
        "agents", "recommendedBranchId", "consensusScore", "summary", "mode", "isDeterministic", "traces",
    },
    "AgentOutput": {"agent_id", "agent_label", "position", "confidence", "rationale", "citations", "concerns"},
    "AvatarChatRequest": {"message", "decisionQuestion", "selectedTimelineId", "simulationContext", "graphNodeIds"},
    "AvatarChatResponse": {
        "content", "referencedNodeIds", "citations", "groundingLabel", "confidence", "llmBacked", "claim_id",
    },
    "IntakeAnalysis": {
        "completenessScore", "missingFields", "assumptions", "clarifyingQuestions", "canProceed",
        "confidencePenalty", "reason",
    },
    "DigitalTwinProfile": {
        "profile_id", "created_at", "subject_type", "inferred_skills", "resources", "constraints", "goals",
        "behavioral_patterns", "decision_history_summary", "risk_profile", "execution_style", "team_topology",
        "missing_information", "contradictions", "confidenceBreakdown", "source_chunk_ids",
        "external_evidence_ids", "methodology",
    },
    "IngestionRun": {
        "run_id", "source_type", "status", "started_at", "completed_at", "chunks_created", "nodes_created",
        "edges_created", "warnings", "errors", "source_summary",
    },
}


def _models():
    from backend.Agents.agent_schema import AgentCouncil, AgentOutput
    from backend.External_Evidence.evidence_schema import EvidenceItem
    from backend.Future_Self.avatar_schema import AvatarChatRequest, AvatarChatResponse
    from backend.Digital_Twin.digital_twin_schema import DigitalTwinProfile
    from backend.Ingestion.ingestion_schema import IngestionRun
    from backend.Intake.intake_schema import IntakeAnalysis
    from backend.simulation_schema import (
        ConfidenceBreakdown,
        SimulationRequest,
        SimulationResponse,
        TimelineBranch,
    )

    return {
        "SimulationRequest": SimulationRequest, "SimulationResponse": SimulationResponse,
        "TimelineBranch": TimelineBranch, "ConfidenceBreakdown": ConfidenceBreakdown,
        "EvidenceItem": EvidenceItem, "AgentCouncil": AgentCouncil, "AgentOutput": AgentOutput,
        "AvatarChatRequest": AvatarChatRequest, "AvatarChatResponse": AvatarChatResponse,
        "IntakeAnalysis": IntakeAnalysis, "DigitalTwinProfile": DigitalTwinProfile,
        "IngestionRun": IngestionRun,
    }


def test_model_field_freeze():
    models = _models()
    for name, frozen in FROZEN_MODEL_FIELDS.items():
        actual = set(models[name].model_fields.keys())
        missing = frozen - actual
        assert not missing, f"{name} lost documented field(s): {sorted(missing)}"


def _client():
    import backend.config as config

    config.LLM_PROVIDER = "mock"
    config.EMBEDDING_PROVIDER = "mock"
    config.AGENT_MODE = "deterministic"
    from fastapi.testclient import TestClient

    import backend.api as api

    return TestClient(api.app)


def _require(obj: dict, fields: set, where: str) -> None:
    missing = fields - set(obj.keys())
    assert not missing, f"{where} response missing field(s): {sorted(missing)}"


def test_health_contract(client=None):
    c = client or _client()
    assert c.get("/health").json() == {"status": "ok"}
    lh = c.get("/llm/health").json()
    _require(lh, {"llm_provider", "embedding_provider", "amd_mode", "chat", "embedding"}, "/llm/health")
    _require(lh["chat"], {"provider", "model", "available", "supports_structured_output", "supports_embeddings", "detail"}, "/llm/health chat")


def test_graph_contract(client=None):
    c = client or _client()
    g = c.get("/graph").json()
    _require(g, {"nodes", "edges"}, "/graph")


def test_evidence_contract(client=None):
    c = client or _client()
    ev = c.get("/evidence").json()
    _require(ev, {"query", "domain", "provider", "isDemoPack", "items"}, "/evidence")
    if ev["items"]:
        from backend.External_Evidence.evidence_schema import EvidenceItem

        EvidenceItem(**ev["items"][0])  # re-validate


def test_intake_contract(client=None):
    c = client or _client()
    ia = c.post("/intake/analyze", json={"decisionQuestion": "Should I pivot?"}).json()
    _require(ia, FROZEN_MODEL_FIELDS["IntakeAnalysis"], "/intake/analyze")
    from backend.Intake.intake_schema import IntakeAnalysis

    IntakeAnalysis(**ia)


def test_digital_twin_contract(client=None):
    c = client or _client()
    dt = c.post("/digital-twin/build", json={"decisionQuestion": "Should I pivot?", "goal": "grow"}).json()
    _require(dt, FROZEN_MODEL_FIELDS["DigitalTwinProfile"], "/digital-twin/build")
    from backend.Digital_Twin.digital_twin_schema import DigitalTwinProfile

    DigitalTwinProfile(**dt)


def test_simulate_contract(client=None):
    c = client or _client()
    resp = c.post("/simulate", json={"name": "Should I pivot to enterprise?", "type": "Startup"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _require(body, FROZEN_MODEL_FIELDS["SimulationResponse"], "/simulate")
    assert body["timelines"], "no timelines returned"
    _require(body["timelines"][0], FROZEN_MODEL_FIELDS["TimelineBranch"], "timeline branch")
    _require(body["timelines"][0]["confidenceBreakdown"], FROZEN_MODEL_FIELDS["ConfidenceBreakdown"], "confidenceBreakdown")
    # Strong shape check: the whole response must still validate against the model.
    from backend.simulation_schema import SimulationResponse

    SimulationResponse(**body)


def test_avatar_contract(client=None):
    c = client or _client()
    av = c.post("/avatar/chat", json={"message": "What first?", "decisionQuestion": "Should I pivot?"}).json()
    _require(av, FROZEN_MODEL_FIELDS["AvatarChatResponse"], "/avatar/chat")
    from backend.Future_Self.avatar_schema import AvatarChatResponse

    AvatarChatResponse(**av)


def run() -> int:
    print("Chronos API contract tests (deterministic/mock)")
    # model freeze first (no client needed)
    try:
        test_model_field_freeze()
        print("  ok - model-field freeze (12 models)")
    except AssertionError as exc:
        print(f"  FAIL - model-field freeze: {exc}")
        return 1

    client = _client()
    live = [
        ("/health + /llm/health", test_health_contract),
        ("/graph", test_graph_contract),
        ("/evidence", test_evidence_contract),
        ("/intake/analyze", test_intake_contract),
        ("/digital-twin/build", test_digital_twin_contract),
        ("/simulate", test_simulate_contract),
        ("/avatar/chat", test_avatar_contract),
    ]
    for label, fn in live:
        try:
            fn(client)
            print(f"  ok - {label}")
        except AssertionError as exc:
            print(f"  FAIL - {label}: {exc}")
            return 1
    print("\nAll contract checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(run())

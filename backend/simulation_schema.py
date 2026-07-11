"""
Shared models for the multi-branch simulation (POST /simulate).

Split out of schema.py so that backend.Agents.agent_council (which needs
SimulationRequest/TimelineBranch/AgentDisagreement) does not have to import
backend.schema — and backend.schema does not have to import back down into
backend.Agents / backend.External_Evidence. This module is a leaf: it only
depends on the two other leaf schema modules (Agents.agent_schema,
External_Evidence.evidence_schema), never on backend.schema itself.

Reuses the heuristic forecast engine internally but varies assumptions across
three branches (Conservative / Balanced / Aggressive). These models mirror the
frontend's timeline.ts contracts so the store can consume them with a thin
adapter. Still a deterministic heuristic — NOT a guaranteed prediction.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.Agents.agent_schema import AgentCouncil
from backend.External_Evidence.evidence_schema import EvidenceItem
from backend.Intake.intake_schema import IntakeAnalysis
from backend.Safety.safety_schema import SafetyLabel

DecisionType = Literal["Career", "Startup", "Financial", "Life", "Relocation"]
Horizon = Literal["1 year", "3 years", "5 years", "10 years"]
MilestoneType = Literal[
    "decision_point", "outcome_realized", "external_event", "skill_milestone", "project_phase"
]
BranchStatus = Literal["active", "archived", "recommended"]

# Mirrors backend.schema.EvidenceType ("fact" | "inference" | "prediction").
# Duplicated (not imported) to keep this module a leaf and avoid a schema.py
# <-> simulation_schema.py import cycle.
_VeracityType = Literal["fact", "inference", "prediction"]


class GroundedDecision(BaseModel):
    """A similar past decision pulled from the existing graph/chunk store, if any."""

    chunk_id: str
    snippet: str
    distance: float
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    timestamp: Optional[str] = None


class Citation(BaseModel):
    """Provenance record; nodeId should resolve to a chunk/graph node when grounded."""

    nodeId: str
    label: str
    excerpt: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    timestamp: Optional[str] = None


class ConfidenceBreakdown(BaseModel):
    evidenceStrength: float = Field(ge=0.0, le=1.0)
    sourceReliability: float = Field(ge=0.0, le=1.0)
    modelConsensus: float = Field(ge=0.0, le=1.0)
    temporalRelevance: float = Field(ge=0.0, le=1.0)
    causalCoherence: float = Field(ge=0.0, le=1.0)


class DataCoverage(BaseModel):
    graphNodes: int = 0
    relevantPrecedents: int = 0
    liveEvidence: int = 0
    demoEvidence: int = 0
    connectorSources: int = 0
    uploadedSources: int = 0
    digitalTwinCompleteness: float = Field(default=0.0, ge=0.0, le=1.0)
    intakeCompleteness: float = Field(default=0.0, ge=0.0, le=1.0)
    overallCoverage: float = Field(default=0.0, ge=0.0, le=1.0)
    gaps: list[str] = Field(default_factory=list)


class TimelineMilestone(BaseModel):
    month: int = Field(ge=0)
    event: str
    type: MilestoneType
    veracity: _VeracityType  # simulated points are "prediction"
    citations: list[Citation] = Field(default_factory=list)
    dataSparsity: float = Field(ge=0.0, le=1.0)


class AgentDisagreement(BaseModel):
    agentId: str
    agentLabel: str
    position: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)


AssumptionType = Literal["market", "resource", "behavior", "timing", "technical", "regulatory"]


class Assumption(BaseModel):
    id: str
    statement: str
    type: AssumptionType
    confidence: float = Field(ge=0.0, le=1.0)
    evidenceIds: list[str] = Field(default_factory=list)
    riskIfWrong: str


class DecisionOption(BaseModel):
    """A concrete choice the user is deciding between. Plain strings from the
    current frontend are coerced into this shape by SimulationRequest."""

    id: Optional[str] = None
    label: str
    description: Optional[str] = None
    upfront_cost: Optional[str] = None
    reversibility: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    time_commitment: Optional[str] = None
    expected_upside: Optional[str] = None
    known_risks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _fill_id(self) -> "DecisionOption":
        if not self.id:
            slug = re.sub(r"[^a-z0-9]+", "_", self.label.lower()).strip("_")[:40] or "option"
            self.id = f"opt_{slug}"
        return self


class SimulationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    type: DecisionType = "Career"
    horizon: Horizon = "3 years"
    risk: int = Field(default=50, ge=0, le=100)
    goal: str = Field(default="Maximize favorable outcome, minimize regret", max_length=500)
    constraints: Optional[str] = None
    geography: Optional[str] = None
    # Accepts DecisionOption objects OR plain strings (current frontend) — strings
    # are coerced into DecisionOption(label=...) so both callers keep working.
    options: list[DecisionOption] = Field(default_factory=list)

    @field_validator("options", mode="before")
    @classmethod
    def _coerce_options(cls, v):
        if not isinstance(v, list):
            return v
        return [{"label": item} if isinstance(item, str) else item for item in v]


class TimelineBranch(BaseModel):
    id: str
    title: str
    description: str
    probabilityScore: float = Field(ge=0.0, le=1.0)
    expectedRegret: float = Field(ge=0.0, le=1.0)
    status: BranchStatus = "active"
    milestones: list[TimelineMilestone] = Field(default_factory=list)
    confidenceBreakdown: ConfidenceBreakdown
    anchorNodeIds: list[str] = Field(default_factory=list)
    agentDisagreements: list[AgentDisagreement] = Field(default_factory=list)
    groundedOn: list[GroundedDecision] = Field(default_factory=list)
    # Curated local demo evidence relevant to this branch (see External_Evidence).
    externalEvidence: list[EvidenceItem] = Field(default_factory=list)

    # --- Option-aware scenario fields (all optional; existing UIs can ignore) ---
    # Set when this branch maps to a user-provided DecisionOption.
    optionId: Optional[str] = None
    assumptions: list[Assumption] = Field(default_factory=list)
    evidenceUsed: list[str] = Field(default_factory=list)  # evidence item ids
    digitalTwinFactors: list[str] = Field(default_factory=list)
    riskFactors: list[str] = Field(default_factory=list)
    upsideFactors: list[str] = Field(default_factory=list)
    failureModes: list[str] = Field(default_factory=list)
    leadingIndicators: list[str] = Field(default_factory=list)
    decisionCheckpoints: list[str] = Field(default_factory=list)
    # Provenance claim ids created for this branch (assumptions / milestones /
    # risk / recommendation). Resolve via GET /provenance/claim/{id}.
    claimIds: list[str] = Field(default_factory=list)


class SimulationMetadata(BaseModel):
    generatedAt: datetime = Field(default_factory=datetime.utcnow)
    schemaVersion: str = "1.0.0"
    query: str
    horizonMonths: int = Field(ge=0)


class SimulationResponse(BaseModel):
    metadata: SimulationMetadata
    timelines: list[TimelineBranch]
    recommendedTimelineId: str
    affectedNodeIds: list[str] = Field(default_factory=list)
    # Immutable snapshot: the exact evidence items used for THIS simulation.
    # Stored by value so changing the evidence store later cannot retroactively
    # alter what a past simulation meant.
    externalEvidenceUsed: list[EvidenceItem] = Field(default_factory=list)
    # How much real, recent, personal/workspace data grounded this run.
    dataCoverage: DataCoverage = Field(default_factory=DataCoverage)
    isDemoEvidence: bool = True
    # Which evidence provider produced the snapshot (demo | uploaded | web | hybrid).
    evidenceProvider: Optional[str] = None
    # Deterministic multi-agent council output (see backend/Agents).
    agentCouncil: Optional[AgentCouncil] = None
    # Digital Twin Constructor output (see backend/Digital_Twin) — id + short
    # summary only, to avoid this module depending on Digital_Twin's schema.
    digitalTwinProfileId: Optional[str] = None
    digitalTwinSummary: Optional[str] = None
    # Clarifying Intake analysis (see backend/Intake): completeness, missing
    # context, assumptions made, and the confidence penalty applied below.
    intakeAnalysis: Optional[IntakeAnalysis] = None
    # Provenance (see backend/Provenance): stable id for this run + a summary of
    # the claim records created for it. Claims resolve via /provenance/*.
    simulationId: Optional[str] = None
    provenanceSummary: Optional[dict] = None
    # Safety label (see backend/Safety): disclaimer always; high-stakes decisions
    # add a professional-advice warning and use conservative confidence.
    safety: Optional[SafetyLabel] = None
    methodology: str = (
        "Structured scenario reasoning aid, not a guaranteed prediction. Three "
        "branches (Conservative / Balanced / Aggressive) are derived from the same "
        "deterministic heuristic engine with varied risk assumptions, seeded off your request "
        "text so repeated calls are stable. Confidence and grounding reflect only "
        "what is available in your graph — treat as a reasoning aid, not a forecast."
    )

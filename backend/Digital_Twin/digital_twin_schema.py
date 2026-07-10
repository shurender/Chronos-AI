"""
Schema for the Digital Twin Constructor (POST /digital-twin/build).

A DigitalTwinProfile is a structured, deterministic-first profile of the
person/team/org being simulated — built from memory-graph nodes, historical
precedents, structured intake, and (optionally) external evidence. It is a
leaf-ish module: only depends on backend.simulation_schema (for DecisionType),
never on backend.Agents/backend.Decision_Graph, so nothing that needs this
schema can create an import cycle.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.simulation_schema import DecisionType

SubjectType = Literal["individual", "team", "org"]


class ProfileItem(BaseModel):
    """One inferred/stated fact about the subject, with provenance."""

    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[str] = Field(default_factory=list)


class RiskProfile(BaseModel):
    level: Literal["low", "moderate", "high", "unknown"] = "unknown"
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)


class ExecutionStyle(BaseModel):
    style: str = "insufficient data"
    rationale: list[str] = Field(default_factory=list)


class TeamTopology(BaseModel):
    size_estimate: int
    roles: list[str] = Field(default_factory=list)


class DigitalTwinConfidenceBreakdown(BaseModel):
    graphCoverage: float = Field(ge=0.0, le=1.0)
    evidenceCoverage: float = Field(ge=0.0, le=1.0)
    intakeCompleteness: float = Field(ge=0.0, le=1.0)
    overallConfidence: float = Field(ge=0.0, le=1.0)


class DigitalTwinBuildRequest(BaseModel):
    decisionQuestion: Optional[str] = None
    decisionType: Optional[DecisionType] = None
    goal: Optional[str] = None
    constraints: Optional[str] = None
    geography: Optional[str] = None
    options: list[str] = Field(default_factory=list)
    useGraph: bool = True
    useEvidence: bool = True


class DigitalTwinProfile(BaseModel):
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    subject_type: SubjectType = "individual"

    inferred_skills: list[ProfileItem] = Field(default_factory=list)
    resources: list[ProfileItem] = Field(default_factory=list)
    constraints: list[ProfileItem] = Field(default_factory=list)
    goals: list[ProfileItem] = Field(default_factory=list)
    behavioral_patterns: list[ProfileItem] = Field(default_factory=list)

    decision_history_summary: str = "No decision history available."
    risk_profile: RiskProfile = Field(default_factory=RiskProfile)
    execution_style: ExecutionStyle = Field(default_factory=ExecutionStyle)
    team_topology: Optional[TeamTopology] = None

    missing_information: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)

    confidenceBreakdown: DigitalTwinConfidenceBreakdown
    source_chunk_ids: list[str] = Field(default_factory=list)
    external_evidence_ids: list[str] = Field(default_factory=list)

    methodology: str = (
        "Deterministic profile built from memory-graph nodes, historical precedents, "
        "structured intake, and external evidence where available. Not an LLM guess — "
        "every item is traceable to a citation, or explicitly listed under "
        "missing_information if it isn't."
    )

"""
Schema for the Clarifying Intake Agent (POST /intake/analyze).

Leaf module: depends only on pydantic (no backend imports), so anything that
needs IntakeAnalysis — including backend.simulation_schema — can import it
without risking a cycle.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

IntakeQuestionCategory = Literal[
    "decision_options",
    "success_metric",
    "time_horizon",
    "geography_domain",
    "risk_tolerance",
    "available_resources",
    "constraints",
    "irreversible_consequences",
    "evidence_gaps",
]


class ClarifyingQuestion(BaseModel):
    category: IntakeQuestionCategory
    question: str
    why_it_matters: str


class IntakeAnalyzeRequest(BaseModel):
    decisionQuestion: str = ""
    decisionType: Optional[str] = None
    horizon: Optional[str] = None
    risk: Optional[int] = None
    goal: Optional[str] = None
    constraints: Optional[str] = None
    geography: Optional[str] = None
    options: list[str] = Field(default_factory=list)
    # Opaque dict (a serialized DigitalTwinProfile) to avoid coupling to that module.
    digitalTwinProfile: Optional[dict] = None
    evidenceCount: Optional[int] = None
    precedentCount: Optional[int] = None


class IntakeAnalysis(BaseModel):
    completenessScore: float = Field(ge=0.0, le=1.0)
    missingFields: list[str] = Field(default_factory=list)
    # What Chronos will assume for each missing field if it proceeds anyway.
    assumptions: list[str] = Field(default_factory=list)
    clarifyingQuestions: list[ClarifyingQuestion] = Field(default_factory=list)
    canProceed: bool = True
    confidencePenalty: float = Field(ge=0.0, le=1.0)
    reason: str

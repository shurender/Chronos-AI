"""
Persistence / replay schema for simulations.

The CORE simulation models (SimulationRequest / SimulationResponse) already live
in backend/simulation_schema.py — this module only adds the stored-record and
replay/diff shapes so a simulation is fully reproducible after the fact.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ReplayMode = Literal["original_evidence", "fresh_evidence"]


class StoredSimulation(BaseModel):
    simulation_id: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request: dict  # serialized SimulationRequest
    response: dict  # full serialized SimulationResponse
    evidence_snapshot: list[dict] = Field(default_factory=list)
    digital_twin_snapshot: Optional[dict] = None
    agent_council_snapshot: Optional[dict] = None
    assumptions: list[dict] = Field(default_factory=list)
    provenance_refs: dict = Field(default_factory=dict)
    methodology_version: str = "heuristic-mvp-1"
    engine_version: str = "1.0.0"


class SimulationSummary(BaseModel):
    """Lightweight list item."""

    simulation_id: str
    created_at: str
    query: str
    recommendedTimelineId: Optional[str] = None


class SimulationDiff(BaseModel):
    probability_delta: float
    regret_delta: float
    confidence_delta: float
    recommendation_changed: bool
    evidence_added: list[str] = Field(default_factory=list)
    evidence_removed: list[str] = Field(default_factory=list)
    explanation: str


class ReplayRequest(BaseModel):
    replay_mode: ReplayMode = "original_evidence"


class ReplayResponse(BaseModel):
    original_simulation_id: str
    replay_simulation_id: str
    replay_mode: ReplayMode
    diff: SimulationDiff
    replay_response: dict

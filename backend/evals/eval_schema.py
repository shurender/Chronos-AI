"""
Schema for Chronos evaluation cases.

An eval case pairs a /simulate (and optionally /avatar/chat) input with the
behaviors we expect and forbid, so quality — not just "it runs" — is checked.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EvalExpectations(BaseModel):
    expected_timelines: Optional[int] = None  # None -> just require >= 1
    min_evidence_count: int = 0
    expected_missing_fields: list[str] = Field(default_factory=list)
    market_should_refuse: bool = False
    confidence_penalty_expected: bool = False
    expected_grounding_labels: list[str] = Field(default_factory=list)  # for avatar
    expected_behaviors: list[str] = Field(default_factory=list)  # documentation
    forbidden_behaviors: list[str] = Field(default_factory=list)  # documentation


class EvalCase(BaseModel):
    id: str
    description: str
    request: dict  # /simulate payload (SimulationRequest shape)
    run_avatar: bool = False
    avatar_message: Optional[str] = None
    critical: bool = True
    expectations: EvalExpectations = Field(default_factory=EvalExpectations)

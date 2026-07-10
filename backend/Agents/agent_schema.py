"""
Schema for the Chronos multi-agent council.

The council is currently a set of DETERMINISTIC structured functions (see
agent_council.py) — not autonomous LLM agents. Each agent reads from decision
intake, memory-graph precedents, external demo evidence, and the heuristic
forecast, and emits a structured position. TODO: optionally back individual
agents with the existing Groq wrapper (backend/llm.py) later.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentOutput(BaseModel):
    agent_id: str
    agent_label: str
    position: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)
    # Memory chunk_ids and/or external evidence ids this agent leaned on.
    citations: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)


class AgentCouncil(BaseModel):
    agents: list[AgentOutput] = Field(default_factory=list)
    recommendedBranchId: str | None = None
    # Consensus derived from agent agreement + confidence (0.0-1.0).
    consensusScore: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = ""
    # Flags that this council is deterministic/heuristic, not LLM-autonomous.
    isDeterministic: bool = True

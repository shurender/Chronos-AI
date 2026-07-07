"""
Pydantic schema for the Decision / Memory Graph.

Every node and edge MUST carry source_chunk_ids + confidence — this is the
trust/citation layer that makes the graph useful (vs. an opaque LLM summary).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

EvidenceType = Literal["fact", "inference", "prediction"]
NodeType = Literal["decision", "outcome", "person", "skill", "project"]
EdgeType = Literal["causal", "temporal", "contributory"]


class Chunk(BaseModel):
    """Shape that the ingestion pipeline must hand off (see build guide section 2)."""

    chunk_id: str
    source_type: Literal["github_commit", "github_issue", "slack_message", "notion_page", "pdf_resume"]
    source_id: str
    raw_text: str
    author: Optional[str] = None
    timestamp: Optional[str] = None  # ISO-8601 UTC, or null
    project: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class GraphNode(BaseModel):
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_type: NodeType
    label: str
    description: str
    source_chunk_ids: list[str]
    evidence_type: EvidenceType
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GraphEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType
    description: str
    source_chunk_ids: list[str]
    evidence_type: EvidenceType
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Wrapper models used to force LLM structured output (see llm.py) ---


class CandidateNode(BaseModel):
    """What we ask the LLM for before we know source_chunk_ids/confidence context.
    We fill node_id/created_at/source_chunk_ids ourselves after the call."""

    node_type: NodeType
    label: str
    description: str


class CandidateNodes(BaseModel):
    nodes: list[CandidateNode]


class CandidateEdge(BaseModel):
    source_label: str  # refer to nodes by label; we resolve to node_id after
    target_label: str
    edge_type: EdgeType
    description: str


class CandidateEdges(BaseModel):
    edges: list[CandidateEdge]


class Tag(BaseModel):
    """Evidence classification for one node or edge, by label/description match."""

    label_or_description: str
    evidence_type: EvidenceType
    confidence: float = Field(ge=0.0, le=1.0)


class Tags(BaseModel):
    tags: list[Tag]


class GapRecord(BaseModel):
    project: Optional[str]
    period: str  # e.g. "2024-07"
    chunk_count: int


class ContradictionRecord(BaseModel):
    contradiction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id_a: str
    node_id_b: str
    note: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Decision Forecast simulator ---
# NOTE ON METHODOLOGY: everything under this section is a deterministic,
# transparent HEURISTIC — not a trained predictive model. It combines a
# type/risk-based profile with (optionally) similar past decisions already
# sitting in the graph. It exists to give a structured, explorable "shape"
# of possible futures, not a guaranteed forecast. The `methodology` field on
# DecisionForecast always says so, and callers/UI should surface it.

DecisionType = Literal["Career", "Startup", "Financial", "Life", "Relocation"]
Horizon = Literal["1 year", "3 years", "5 years", "10 years"]
OutcomeLabel = Literal["Failure", "Survival", "Modest", "Strong", "Breakout"]
RiskCategory = Literal["Financial", "Career", "Health", "Relationships", "Reputation", "Time"]


class DecisionForecastRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    type: DecisionType
    horizon: Horizon
    risk: int = Field(ge=0, le=100)
    goal: str = Field(..., min_length=1, max_length=500)


class ProbabilityOutcome(BaseModel):
    outcome: OutcomeLabel
    value: float = Field(ge=0.0, le=100.0)


class ForecastPoint(BaseModel):
    month: str  # e.g. "M0", "M12"
    value: float = Field(ge=0.0, le=100.0)


class RiskHeatmapItem(BaseModel):
    label: RiskCategory
    level: float = Field(ge=0.0, le=100.0)


class RegretAnalysis(BaseModel):
    regretScore: int = Field(ge=0, le=100)
    inactionRegretScore: int = Field(ge=0, le=100)
    summary: str


class GroundedDecision(BaseModel):
    """A similar past decision pulled from the existing graph/chunk store, if any."""

    chunk_id: str
    snippet: str
    distance: float


class DecisionForecast(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    request: DecisionForecastRequest
    probabilityDistribution: list[ProbabilityOutcome]
    successForecast: list[ForecastPoint]
    riskHeatmap: list[RiskHeatmapItem]
    regretAnalysis: RegretAnalysis
    groundedOn: list[GroundedDecision] = Field(default_factory=list)
    methodology: str = (
        "Heuristic estimate derived from decision type, stated risk, and horizon, "
        "optionally nudged by similar past decisions found in your graph. Not a "
        "statistical or ML-trained prediction — treat as a structured prompt for "
        "thinking, not a guarantee."
    )


    # --- Memory Vault (append to schema.py) ---

MemoryVaultNodeType = Literal["current_you", "decision", "future_paths"]


class MemoryVaultGraphNode(BaseModel):
    id: str
    nodeType: MemoryVaultNodeType
    label: str
    year: Optional[int] = None


class MemoryVaultGraphEdge(BaseModel):
    source: str
    target: str
    animated: bool = True


class MemoryEntry(BaseModel):
    nodeId: str
    year: int
    title: str
    outcome: str
    lesson: str
    connectsTo: list[str] = Field(default_factory=list)
    sourceChunkIds: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    expandedByDefault: bool = False


class MemoryVaultResponse(BaseModel):
    graphNodes: list[MemoryVaultGraphNode]
    graphEdges: list[MemoryVaultGraphEdge]
    memoryEntries: list[MemoryEntry]
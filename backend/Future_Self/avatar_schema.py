"""
Schema for the Future Self avatar chat (POST /avatar/chat).

The avatar answers as the user's "Future Self" WITHIN a selected simulated
timeline. It grounds answers in memory-graph precedents and/or the External
Evidence Layer, and is explicit about when it is reasoning generally instead.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

GroundingLabel = Literal[
    "graph_grounded",  # backed by memory-graph precedents
    "evidence_grounded",  # backed by external demo evidence
    "mixed",  # backed by both
    "general_opinion",  # no grounding available -> low confidence
]


class AvatarCitation(BaseModel):
    nodeId: str
    label: str
    excerpt: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    timestamp: Optional[str] = None


class AvatarChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    decisionQuestion: Optional[str] = None
    selectedTimelineId: Optional[str] = None
    simulationContext: Optional[dict] = None
    graphNodeIds: Optional[list[str]] = None


class AvatarChatResponse(BaseModel):
    content: str
    referencedNodeIds: list[str] = Field(default_factory=list)
    citations: list[AvatarCitation] = Field(default_factory=list)
    groundingLabel: GroundingLabel
    confidence: float = Field(ge=0.0, le=1.0)
    # True when a real LLM produced the text; False for the deterministic fallback.
    llmBacked: bool = False
    llmProvider: Optional[str] = None
    fallbackReason: Optional[str] = None
    # Provenance claim id for this answer (resolve via GET /provenance/claim/{id}).
    claim_id: Optional[str] = None

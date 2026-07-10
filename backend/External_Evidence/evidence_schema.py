"""
Schema for the External Evidence Intelligence Layer.

NOTE: This is a CURATED LOCAL DEMO evidence pack, not a live web search. Every
item is clearly sourced to the "Chronos Demo Evidence Pack" and callers/UI must
surface that it is demo/local evidence, not real-time external claims.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

EvidenceType = Literal[
    "market_signal",
    "research_signal",
    "job_signal",
    "competitor_signal",
    "regulatory_signal",
    "user_supplied",
]

SourceKind = Literal["demo", "uploaded", "web"]


class EvidenceItem(BaseModel):
    id: str
    domain: str
    title: str
    summary: str
    source_name: str
    source_url: Optional[str] = None
    published_at: Optional[str] = None  # ISO date, or null
    evidence_type: EvidenceType
    confidence: float = Field(ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)

    # --- Source quality / provenance (defaults describe curated demo evidence,
    #     so existing demo_evidence.json loads unchanged) ---
    source_kind: SourceKind = "demo"
    retrieved_at: Optional[str] = None  # ISO timestamp when fetched/uploaded, or null
    freshness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    source_reliability: float = Field(default=0.5, ge=0.0, le=1.0)
    is_live_source: bool = False
    is_demo_source: bool = True


class EvidenceUploadRequest(BaseModel):
    """User-supplied evidence. Either `summary` or `text` must be provided."""

    title: Optional[str] = None
    summary: Optional[str] = None
    text: Optional[str] = None  # alias for summary when only raw text is sent
    domain: str = "user"
    source_name: str = "User Upload"
    source_url: Optional[str] = None
    evidence_type: EvidenceType = "user_supplied"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    published_at: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class EvidenceSearchResponse(BaseModel):
    query: Optional[str] = None
    domain: Optional[str] = None
    provider: str = "demo"
    isDemoPack: bool = True
    items: list[EvidenceItem] = Field(default_factory=list)

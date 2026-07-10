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


class EvidenceSearchResponse(BaseModel):
    query: Optional[str] = None
    domain: Optional[str] = None
    isDemoPack: bool = True
    items: list[EvidenceItem] = Field(default_factory=list)

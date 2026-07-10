"""Schema for safety/privacy controls. Leaf module (pydantic only)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RedactRequest(BaseModel):
    text: str


class RedactResponse(BaseModel):
    redacted_text: str
    categories_detected: list[str] = Field(default_factory=list)
    redaction_count: int = 0
    was_redacted: bool = False


class SafetyLabel(BaseModel):
    """Attached to simulation output — always carries a disclaimer; high-stakes
    decisions add a professional-advice warning."""

    disclaimer: str
    high_stakes: bool = False
    category: str = ""  # decision type
    professional_advice_warning: Optional[str] = None


class PolicyResponse(BaseModel):
    policies: list[str] = Field(default_factory=list)
    high_stakes_types: list[str] = Field(default_factory=list)
    store_raw_unredacted: bool = False
    data_retention_days: int = 0

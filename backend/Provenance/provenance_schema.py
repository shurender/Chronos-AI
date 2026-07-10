"""
Provenance schema — canonical SourceRecord and ClaimRecord.

Leaf module: pydantic + a small regex PII-redaction hook only, so anything can
depend on it without an import cycle. Records are persisted by
provenance_service (SQLite).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ClaimType = Literal["fact", "inference", "prediction", "recommendation"]
ClaimAuthor = Literal["extraction_pipeline", "agent", "evidence_provider", "simulation", "avatar"]


# --- PII redaction hook -----------------------------------------------------
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# API-key / secret-ish tokens (OpenAI, Groq, GitHub, AWS, Slack).
_SECRET_RE = re.compile(r"\b(?:sk-|gsk_|ghp_|github_pat_|AKIA|xox[baprs]-)[A-Za-z0-9_\-]{8,}\b")
# Phone-like: optional +, then 10+ digits allowing common separators.
_PHONE_RE = re.compile(r"(?<!\w)\+?\d(?:[\d\s().-]{8,})\d(?!\w)")


def _looks_like_phone(match: str) -> bool:
    return sum(c.isdigit() for c in match) >= 10


def redact_pii(text: str) -> tuple[str, bool]:
    """Redact emails, obvious secrets, and phone-like numbers. Returns
    (redacted_text, was_redacted). Conservative — a hook, not a DLP system."""
    if not text:
        return text, False
    redacted = _EMAIL_RE.sub("[redacted-email]", text)
    redacted = _SECRET_RE.sub("[redacted-secret]", redacted)
    redacted = _PHONE_RE.sub(
        lambda m: "[redacted-phone]" if _looks_like_phone(m.group(0)) else m.group(0), redacted
    )
    return redacted, redacted != text


# --- Records ----------------------------------------------------------------
class SourceRecord(BaseModel):
    source_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str  # e.g. github_commit, slack_message, uploaded_file, evidence_pack
    source_name: str
    uri: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    author: Optional[str] = None
    timestamp: Optional[str] = None
    project: Optional[str] = None
    raw_excerpt: str = ""
    metadata: dict = Field(default_factory=dict)
    pii_redacted: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ClaimRecord(BaseModel):
    claim_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim_text: str
    claim_type: ClaimType
    created_by: ClaimAuthor
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    graph_node_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    uncertainty_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    # Linkage for /provenance/timeline and /provenance/simulation lookups.
    timeline_id: Optional[str] = None
    simulation_id: Optional[str] = None


class ProvenanceSummary(BaseModel):
    simulation_id: str
    total_claims: int
    claims_by_type: dict[str, int] = Field(default_factory=dict)

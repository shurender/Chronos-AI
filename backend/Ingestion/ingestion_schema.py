"""
Schema for API-driven ingestion (POST /ingest/*).

An IngestionRun is a persisted record of one ingestion attempt (demo / github /
upload), independent of the graph itself, so callers can audit what happened.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from typing import Literal

IngestionSourceType = Literal["demo", "github", "upload"]
IngestionStatus = Literal["pending", "running", "succeeded", "failed"]


class IngestionRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: IngestionSourceType
    status: IngestionStatus = "pending"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    chunks_created: int = 0
    nodes_created: int = 0
    edges_created: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    source_summary: dict = Field(default_factory=dict)


class IngestGithubRequest(BaseModel):
    repo: str = Field(..., min_length=1, description="'owner/repo' or a GitHub URL")
    include_issues: bool = True
    max_items: int = Field(default=30, ge=1, le=200)


class IngestResetResponse(BaseModel):
    reset: bool
    nodes_before: int
    edges_before: int

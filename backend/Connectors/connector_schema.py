from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.Ingestion.ingestion_schema import IngestionRun

ConnectorProvider = Literal["github", "slack", "notion"]
ConnectorState = Literal["not_connected", "connecting", "connected", "syncing", "error"]


class ConnectorAccount(BaseModel):
    provider: ConnectorProvider
    account_id: str | None = None
    display_name: str | None = None
    access_token: str
    refresh_token: str | None = None
    scopes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class ConnectorStatus(BaseModel):
    provider: ConnectorProvider
    status: ConnectorState
    connected: bool = False
    account_id: str | None = None
    display_name: str | None = None
    last_synced: str | None = None
    last_sync_at: str | None = None
    last_sync_status: str | None = None
    error: str | None = None
    last_error: str | None = None
    scopes: list[str] = Field(default_factory=list)
    items_ingested: int = 0
    source_counts: dict[str, int] = Field(default_factory=dict)


class ConnectorSyncRequest(BaseModel):
    repo: str | None = None
    channel_ids: list[str] | None = None
    page_ids: list[str] | None = None
    sourceIds: list[str] | None = None
    max_items: int = Field(default=50, ge=1, le=200)
    maxItems: int | None = Field(default=None, ge=1, le=200)
    since: str | None = None
    includeThreads: bool = True
    includeIssues: bool = True
    includePullRequests: bool = True


class ConnectorSyncResponse(BaseModel):
    provider: ConnectorProvider
    status: ConnectorState
    run: IngestionRun | None = None
    last_synced: str | None = None
    source_counts: dict[str, int] = Field(default_factory=dict)
    error: str | None = None


class ConnectorSourceSelection(BaseModel):
    sourceIds: list[str] = Field(default_factory=list)


class GithubSource(BaseModel):
    id: str
    name: str
    full_name: str
    private: bool
    html_url: str | None = None
    updated_at: str | None = None
    default_branch: str | None = None
    selected: bool = False


class SlackSource(BaseModel):
    id: str
    name: str
    is_private: bool
    is_member: bool
    num_members: int | None = None
    selected: bool = False


class NotionSource(BaseModel):
    id: str
    title: str
    type: Literal["page", "database"]
    url: str | None = None
    last_edited_time: str | None = None
    selected: bool = False

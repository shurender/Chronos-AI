from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from .connector_schema import (
    ConnectorProvider,
    ConnectorSourceSelection,
    ConnectorStatus,
    ConnectorSyncRequest,
    ConnectorSyncResponse,
    GithubSource,
    NotionSource,
    SlackSource,
)
from .connector_store import delete_account, get_selected_sources, list_statuses, set_selected_sources
from .sync_state import list_states, reset_state
from .providers import github_connector, notion_connector, slack_connector

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("", response_model=list[ConnectorStatus])
def connectors():
    return list_statuses()


@router.get("/status", response_model=list[ConnectorStatus])
def connector_status():
    return list_statuses()


@router.post("/{provider}/sources/select", response_model=ConnectorSourceSelection)
def select_sources(provider: ConnectorProvider, request: ConnectorSourceSelection):
    return ConnectorSourceSelection(sourceIds=set_selected_sources(provider, request.sourceIds))


@router.get("/{provider}/sources/selected", response_model=ConnectorSourceSelection)
def selected_sources(provider: ConnectorProvider):
    return ConnectorSourceSelection(sourceIds=get_selected_sources(provider))


@router.get("/{provider}/sync-state")
def sync_state(provider: ConnectorProvider):
    return {"provider": provider, "sources": [state.model_dump(mode="json") for state in list_states(provider)]}


@router.post("/{provider}/reset-sync-state")
def reset_sync_state(provider: ConnectorProvider):
    return {"provider": provider, "reset": reset_state(provider)}


@router.post("/{provider}/resync-full", response_model=ConnectorSyncResponse)
def resync_full(provider: ConnectorProvider, request: ConnectorSyncRequest | None = None):
    reset_state(provider, (request.sourceIds if request else None))
    request = request or ConnectorSyncRequest()
    request.since = None
    if provider == "github":
        return github_connector.sync(request)
    if provider == "slack":
        return slack_connector.sync(request)
    return notion_connector.sync(request)


@router.get("/github/start")
def github_start() -> RedirectResponse:
    return github_connector.start()


@router.get("/github/sources", response_model=list[GithubSource])
def github_sources():
    return github_connector.sources()


@router.get("/github/callback")
def github_callback(code: str | None = None, state: str | None = None) -> RedirectResponse:
    return github_connector.callback(code, state)


@router.post("/github/sync", response_model=ConnectorSyncResponse)
def github_sync(request: ConnectorSyncRequest | None = None):
    return github_connector.sync(request or ConnectorSyncRequest())


@router.post("/github/disconnect", response_model=ConnectorStatus)
def github_disconnect():
    return delete_account("github")


@router.get("/slack/start")
def slack_start() -> RedirectResponse:
    return slack_connector.start()


@router.get("/slack/sources", response_model=list[SlackSource])
def slack_sources():
    return slack_connector.sources()


@router.get("/slack/callback")
def slack_callback(code: str | None = None, state: str | None = None) -> RedirectResponse:
    return slack_connector.callback(code, state)


@router.post("/slack/sync", response_model=ConnectorSyncResponse)
def slack_sync(request: ConnectorSyncRequest | None = None):
    return slack_connector.sync(request or ConnectorSyncRequest())


@router.post("/slack/disconnect", response_model=ConnectorStatus)
def slack_disconnect():
    return delete_account("slack")


@router.get("/notion/start")
def notion_start() -> RedirectResponse:
    return notion_connector.start()


@router.get("/notion/sources", response_model=list[NotionSource])
def notion_sources():
    return notion_connector.sources()


@router.get("/notion/callback")
def notion_callback(code: str | None = None, state: str | None = None) -> RedirectResponse:
    return notion_connector.callback(code, state)


@router.post("/notion/sync", response_model=ConnectorSyncResponse)
def notion_sync(request: ConnectorSyncRequest | None = None):
    return notion_connector.sync(request or ConnectorSyncRequest())


@router.post("/notion/disconnect", response_model=ConnectorStatus)
def notion_disconnect():
    return delete_account("notion")

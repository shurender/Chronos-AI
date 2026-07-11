from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from backend import config
from backend.Ingestion.ingestion_service import ingest_connector_chunks
from backend.ingestion_pipeline.parsers.slack_parser import parse_slack_export

from ..connector_schema import ConnectorAccount, ConnectorSyncRequest, ConnectorSyncResponse, SlackSource
from ..connector_store import consume_oauth_state, create_oauth_state, get_account, get_selected_sources, save_account, set_status
from ..sync_state import get_state, update_state


def start() -> RedirectResponse:
    if not config.SLACK_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Slack OAuth is not configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET.")
    state = create_oauth_state("slack")
    params = {
        "client_id": config.SLACK_CLIENT_ID,
        "redirect_uri": config.SLACK_REDIRECT_URI,
        "scope": "channels:history channels:read groups:history groups:read users:read files:read links:read",
        "state": state,
    }
    return RedirectResponse(f"https://slack.com/oauth/v2/authorize?{httpx.QueryParams(params)}")


def callback(code: str | None, state: str | None) -> RedirectResponse:
    if not code or not consume_oauth_state(state, "slack"):
        raise HTTPException(status_code=400, detail="Invalid Slack OAuth callback.")
    if not config.SLACK_CLIENT_ID or not config.SLACK_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Slack OAuth is not configured.")
    with httpx.Client(timeout=15.0) as client:
        res = client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": config.SLACK_CLIENT_ID,
                "client_secret": config.SLACK_CLIENT_SECRET,
                "code": code,
                "redirect_uri": config.SLACK_REDIRECT_URI,
            },
        )
        res.raise_for_status()
        body = res.json()
    if not body.get("ok") or not body.get("access_token"):
        raise HTTPException(status_code=502, detail=body.get("error") or "Slack did not return an access token.")
    save_account(
        ConnectorAccount(
            provider="slack",
            account_id=(body.get("team") or {}).get("id"),
            display_name=(body.get("team") or {}).get("name") or "Slack",
            access_token=body["access_token"],
            scopes=[scope.strip() for scope in (body.get("scope") or "").split(",") if scope.strip()],
        )
    )
    return RedirectResponse("http://localhost:5173/?connector=slack&status=connected")


def sync(request: ConnectorSyncRequest) -> ConnectorSyncResponse:
    set_status("slack", status="syncing", error=None, last_sync_status="running")
    account = get_account("slack")
    if not account:
        set_status("slack", status="error", connected=False, error="Connect Slack before syncing.")
        raise HTTPException(status_code=401, detail="Connect Slack before syncing.")
    try:
        source_ids = request.sourceIds or request.channel_ids or get_selected_sources("slack")
        if not source_ids:
            message = "Select one or more Slack channels before syncing."
            set_status("slack", status="error", last_sync_status="failed", error=message)
            raise HTTPException(status_code=422, detail=message)
        request.channel_ids = source_ids
        chunks, counts = _fetch_chunks(account.access_token, request)
        run = ingest_connector_chunks("slack", chunks, counts)
        if run.status == "failed":
            raise RuntimeError("; ".join(run.errors) or "Slack ingestion failed.")
        now = datetime.utcnow().isoformat()
        counts.update({key: value for key, value in run.source_summary.items() if isinstance(value, int)})
        counts.update({"chunks": run.chunks_created, "nodes": run.nodes_created, "edges": run.edges_created, "nodes_created": run.nodes_created, "edges_created": run.edges_created})
        set_status("slack", status="connected", connected=True, last_synced=now, last_sync_status="succeeded", error=None, source_counts=counts, items_ingested=run.chunks_created)
        return ConnectorSyncResponse(provider="slack", status="connected", run=run, last_synced=now, source_counts=counts)
    except Exception as exc:
        message = str(exc)
        set_status("slack", status="error", last_sync_status="failed", error=message)
        raise HTTPException(status_code=502, detail=message) from exc


def _slack_get(client: httpx.Client, path: str, **params):
    res = client.get(f"https://slack.com/api/{path}", params=params)
    res.raise_for_status()
    body = res.json()
    if not body.get("ok"):
        raise RuntimeError(body.get("error") or f"Slack {path} failed")
    return body


def sources() -> list[SlackSource]:
    account = get_account("slack")
    if not account:
        raise HTTPException(status_code=401, detail="Connect Slack before listing channels.")
    selected = set(get_selected_sources("slack"))
    headers = {"Authorization": f"Bearer {account.access_token}"}
    with httpx.Client(timeout=15.0, headers=headers) as client:
        body = _slack_get(client, "conversations.list", types="public_channel,private_channel", limit=200)
    channels = body.get("channels", [])
    return [
        SlackSource(
            id=channel.get("id") or "",
            name=channel.get("name") or channel.get("id") or "unknown",
            is_private=bool(channel.get("is_private")),
            is_member=bool(channel.get("is_member")),
            num_members=channel.get("num_members"),
            selected=channel.get("id") in selected,
        )
        for channel in channels
        if channel.get("id")
    ]


def _fetch_chunks(token: str, request: ConnectorSyncRequest) -> tuple[list[dict], dict[str, int]]:
    headers = {"Authorization": f"Bearer {token}"}
    max_items = max(1, min(request.max_items, 200))
    chunks: list[dict] = []
    counts = {"channels": 0, "messages": 0, "threads": 0}
    with httpx.Client(timeout=20.0, headers=headers) as client:
        channels_body = _slack_get(client, "conversations.list", types="public_channel,private_channel", limit=100)
        channels = channels_body.get("channels", [])
        if request.channel_ids:
            channels = [ch for ch in channels if ch.get("id") in request.channel_ids]
        for channel in channels[:10]:
            if channel.get("is_private") and not channel.get("is_member"):
                continue
            channel_id = channel.get("id")
            channel_name = channel.get("name") or channel_id or "unknown"
            state = get_state("slack", channel_id)
            history_params = {"channel": channel_id, "limit": max_items}
            if request.since:
                history_params["oldest"] = request.since
            elif state and state.last_cursor:
                history_params["oldest"] = state.last_cursor
            history = _slack_get(client, "conversations.history", **history_params).get("messages", [])
            permalinks: dict[str, str] = {}
            for msg in history[:20]:
                if msg.get("ts"):
                    try:
                        permalink_body = _slack_get(client, "chat.getPermalink", channel=channel_id, message_ts=msg["ts"])
                        permalinks[msg["ts"]] = permalink_body.get("permalink")
                    except Exception:
                        pass
            counts["channels"] += 1
            counts["messages"] += len(history)
            for msg in list(history):
                if request.includeThreads and msg.get("reply_count"):
                    replies = _slack_get(client, "conversations.replies", channel=channel_id, ts=msg["ts"], limit=50).get("messages", [])
                    history.extend(replies[1:])
                    counts["threads"] += 1
            parsed = parse_slack_export(history, channel_name)
            for chunk in parsed:
                meta = chunk.setdefault("metadata", {})
                ts = str(chunk.get("source_id") or meta.get("ts") or "")
                thread_ts = str(meta.get("thread_ts") or "")
                chunk["chunk_id"] = f"slack:{channel_id}:{thread_ts}:{ts}" if thread_ts and thread_ts != ts else f"slack:{channel_id}:{ts}"
                meta.update(
                    {
                        "connector_provider": "slack",
                        "connector_source_id": channel_id,
                        "source_name": f"#{channel_name}",
                        "source_auth": "authenticated",
                        "source_live": True,
                        "channel": channel_name,
                        "channel_id": channel_id,
                        "external_id": ts,
                        "source_url": permalinks.get(str(chunk.get("source_id"))) or f"slack://channel/{channel_id}/message/{ts}",
                        "permalink": permalinks.get(str(chunk.get("source_id"))),
                    }
                )
            chunks.extend(parsed)
            newest_ts = max((str(msg.get("ts")) for msg in history if msg.get("ts")), default=None)
            update_state(
                "slack",
                channel_id,
                source_name=channel_name,
                last_cursor=newest_ts,
                seen_item_ids=[chunk["chunk_id"] for chunk in parsed],
                item_count=len(parsed),
            )
    return chunks, counts

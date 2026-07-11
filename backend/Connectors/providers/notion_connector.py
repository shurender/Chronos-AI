from __future__ import annotations

import base64
from datetime import datetime

import httpx
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from backend import config
from backend.Ingestion.ingestion_service import ingest_connector_chunks

from ..connector_schema import ConnectorAccount, ConnectorSyncRequest, ConnectorSyncResponse, NotionSource
from ..connector_store import consume_oauth_state, create_oauth_state, get_account, get_selected_sources, save_account, set_status
from ..sync_state import get_state, update_state


def start() -> RedirectResponse:
    if not config.NOTION_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Notion OAuth is not configured. Set NOTION_CLIENT_ID and NOTION_CLIENT_SECRET.")
    state = create_oauth_state("notion")
    params = {
        "client_id": config.NOTION_CLIENT_ID,
        "redirect_uri": config.NOTION_REDIRECT_URI,
        "response_type": "code",
        "owner": "user",
        "state": state,
    }
    return RedirectResponse(f"https://api.notion.com/v1/oauth/authorize?{httpx.QueryParams(params)}")


def callback(code: str | None, state: str | None) -> RedirectResponse:
    if not code or not consume_oauth_state(state, "notion"):
        raise HTTPException(status_code=400, detail="Invalid Notion OAuth callback.")
    if not config.NOTION_CLIENT_ID or not config.NOTION_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Notion OAuth is not configured.")
    basic = base64.b64encode(f"{config.NOTION_CLIENT_ID}:{config.NOTION_CLIENT_SECRET}".encode("utf-8")).decode("ascii")
    with httpx.Client(timeout=15.0) as client:
        res = client.post(
            "https://api.notion.com/v1/oauth/token",
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/json", "Notion-Version": config.NOTION_VERSION},
            json={"grant_type": "authorization_code", "code": code, "redirect_uri": config.NOTION_REDIRECT_URI},
        )
        res.raise_for_status()
        body = res.json()
    token = body.get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="Notion did not return an access token.")
    owner = body.get("owner") or {}
    user = owner.get("user") or {}
    save_account(
        ConnectorAccount(
            provider="notion",
            account_id=body.get("workspace_id") or user.get("id"),
            display_name=body.get("workspace_name") or user.get("name") or "Notion",
            access_token=token,
            scopes=[],
        )
    )
    return RedirectResponse("http://localhost:5173/?connector=notion&status=connected")


def sync(request: ConnectorSyncRequest) -> ConnectorSyncResponse:
    set_status("notion", status="syncing", error=None, last_sync_status="running")
    account = get_account("notion")
    token = (account.access_token if account else None) or config.NOTION_TOKEN
    if not token:
        set_status("notion", status="error", connected=False, error="Connect Notion or set NOTION_TOKEN before syncing.")
        raise HTTPException(status_code=401, detail="Connect Notion or set NOTION_TOKEN before syncing.")
    try:
        source_ids = request.sourceIds or request.page_ids or get_selected_sources("notion")
        if not source_ids:
            message = "Select one or more Notion pages or databases before syncing."
            set_status("notion", status="error", last_sync_status="failed", error=message)
            raise HTTPException(status_code=422, detail=message)
        request.page_ids = source_ids
        chunks, counts = _fetch_chunks(token, request)
        run = ingest_connector_chunks("notion", chunks, counts)
        if run.status == "failed":
            raise RuntimeError("; ".join(run.errors) or "Notion ingestion failed.")
        now = datetime.utcnow().isoformat()
        counts.update({key: value for key, value in run.source_summary.items() if isinstance(value, int)})
        counts.update({"chunks": run.chunks_created, "nodes": run.nodes_created, "edges": run.edges_created, "nodes_created": run.nodes_created, "edges_created": run.edges_created})
        set_status("notion", status="connected", connected=True, last_synced=now, last_sync_status="succeeded", error=None, source_counts=counts, items_ingested=run.chunks_created)
        return ConnectorSyncResponse(provider="notion", status="connected", run=run, last_synced=now, source_counts=counts)
    except Exception as exc:
        message = str(exc)
        set_status("notion", status="error", last_sync_status="failed", error=message)
        raise HTTPException(status_code=502, detail=message) from exc


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Notion-Version": config.NOTION_VERSION, "Content-Type": "application/json"}


def sources() -> list[NotionSource]:
    account = get_account("notion")
    token = (account.access_token if account else None) or config.NOTION_TOKEN
    if not token:
        raise HTTPException(status_code=401, detail="Connect Notion or set NOTION_TOKEN before listing sources.")
    selected = set(get_selected_sources("notion"))
    with httpx.Client(timeout=15.0, headers=_headers(token)) as client:
        res = client.post("https://api.notion.com/v1/search", json={"page_size": 100})
        res.raise_for_status()
        results = res.json().get("results", [])
    return [
        NotionSource(
            id=item.get("id") or "",
            title=_page_title(item) if item.get("object") == "page" else _database_title(item),
            type="database" if item.get("object") == "database" else "page",
            url=item.get("url"),
            last_edited_time=item.get("last_edited_time"),
            selected=item.get("id") in selected,
        )
        for item in results
        if item.get("id") and item.get("object") in {"page", "database"}
    ]


def _fetch_chunks(token: str, request: ConnectorSyncRequest) -> tuple[list[dict], dict[str, int]]:
    max_items = max(1, min(request.max_items, 200))
    chunks: list[dict] = []
    counts = {"pages": 0, "blocks": 0, "databases": 0}
    with httpx.Client(timeout=20.0, headers=_headers(token)) as client:
        if request.page_ids:
            pages = []
            for source_id in request.page_ids:
                item = _get_page_or_database(client, source_id)
                if item.get("object") == "database":
                    counts["databases"] += 1
                    pages.extend(_query_database_pages(client, source_id, limit=max_items))
                else:
                    pages.append(item)
        else:
            search = client.post("https://api.notion.com/v1/search", json={"page_size": min(max_items, 100)})
            search.raise_for_status()
            results = search.json().get("results", [])
            pages = [item for item in results if item.get("object") == "page"]
            counts["databases"] = sum(1 for item in results if item.get("object") == "database")
        for page in pages[:max_items]:
            page_id = page.get("id")
            title = _page_title(page)
            state = get_state("notion", page_id)
            last_sync = request.since or (state.last_sync_at if state else None)
            if last_sync and page.get("last_edited_time") and str(page.get("last_edited_time")) <= str(last_sync):
                continue
            blocks = _blocks(client, page_id, limit=100)
            counts["pages"] += 1
            counts["blocks"] += len(blocks)
            page_chunks = _page_chunks(page, blocks, title)
            chunks.extend(page_chunks)
            update_state(
                "notion",
                page_id,
                source_name=title,
                last_cursor=page.get("last_edited_time"),
                seen_item_ids=[chunk["chunk_id"] for chunk in page_chunks],
                item_count=len(page_chunks),
            )
    return chunks, counts


def _page_chunks(page: dict, blocks: list[dict], title: str) -> list[dict]:
    page_id = page.get("id")
    page_chunks = []
    for block in blocks:
        text = _block_text(block)
        block_id = block.get("id")
        if not text or not block_id:
            continue
        page_chunks.append(
            {
                "chunk_id": f"notion:{page_id}:{block_id}",
                "source_type": "notion_page",
                "source_id": block_id,
                "raw_text": f"Notion Page: {title}\n\n{text}",
                "author": None,
                "timestamp": page.get("last_edited_time"),
                "project": title,
                "metadata": {
                    "connector_provider": "notion",
                    "connector_source_id": page_id,
                    "source_name": title,
                    "source_auth": "authenticated",
                    "source_live": True,
                    "page_id": page_id,
                    "page_title": title,
                    "block_id": block_id,
                    "external_id": block_id,
                    "last_edited_time": page.get("last_edited_time"),
                    "source_url": page.get("url"),
                    "url": page.get("url"),
                },
            }
        )
    if not page_chunks:
        page_chunks.append(
            {
                "chunk_id": f"notion:{page_id}:summary",
                "source_type": "notion_page",
                "source_id": page_id,
                "raw_text": f"Notion Page: {title}",
                "author": None,
                "timestamp": page.get("last_edited_time"),
                "project": title,
                "metadata": {
                    "connector_provider": "notion",
                    "connector_source_id": page_id,
                    "source_name": title,
                    "source_auth": "authenticated",
                    "source_live": True,
                    "page_id": page_id,
                    "page_title": title,
                    "external_id": page_id,
                    "last_edited_time": page.get("last_edited_time"),
                    "source_url": page.get("url"),
                    "url": page.get("url"),
                },
            }
        )
    return page_chunks


def _get_page(client: httpx.Client, page_id: str) -> dict:
    res = client.get(f"https://api.notion.com/v1/pages/{page_id}")
    res.raise_for_status()
    return res.json()


def _get_page_or_database(client: httpx.Client, source_id: str) -> dict:
    page_res = client.get(f"https://api.notion.com/v1/pages/{source_id}")
    if page_res.status_code == 200:
        return page_res.json()
    db_res = client.get(f"https://api.notion.com/v1/databases/{source_id}")
    db_res.raise_for_status()
    return db_res.json()


def _query_database_pages(client: httpx.Client, database_id: str, limit: int) -> list[dict]:
    res = client.post(f"https://api.notion.com/v1/databases/{database_id}/query", json={"page_size": min(limit, 100)})
    res.raise_for_status()
    return [item for item in res.json().get("results", []) if item.get("object") == "page"]


def _blocks(client: httpx.Client, block_id: str, limit: int) -> list[dict]:
    res = client.get(f"https://api.notion.com/v1/blocks/{block_id}/children", params={"page_size": limit})
    res.raise_for_status()
    blocks = res.json().get("results", [])
    nested: list[dict] = []
    for block in blocks:
        nested.append(block)
        if block.get("has_children"):
            nested.extend(_blocks(client, block["id"], limit=50))
    return nested


def _page_title(page: dict) -> str:
    for prop in (page.get("properties") or {}).values():
        title = prop.get("title")
        if title:
            return "".join(part.get("plain_text", "") for part in title) or "Untitled"
    return "Untitled"


def _database_title(database: dict) -> str:
    title = database.get("title") or []
    return "".join(part.get("plain_text", "") for part in title) or "Untitled database"


def _block_text(block: dict) -> str:
    block_type = block.get("type")
    payload = block.get(block_type) or {}
    rich = payload.get("rich_text") or []
    text = "".join(part.get("plain_text", "") for part in rich).strip()
    if not text:
        return ""
    if block_type in {"heading_1", "heading_2", "heading_3"}:
        return f"## {text}"
    if block_type in {"bulleted_list_item", "numbered_list_item", "to_do"}:
        return f"- {text}"
    return text

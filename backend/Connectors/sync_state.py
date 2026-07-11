from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from backend import config

Provider = Literal["github", "slack", "notion"]

_lock = threading.Lock()


class SourceSyncState(BaseModel):
    provider: Provider
    source_id: str
    source_name: str | None = None
    last_sync_at: str | None = None
    last_cursor: str | None = None
    last_seen_item_ids: list[str] = Field(default_factory=list)
    item_count: int = 0
    status: str = "never_synced"
    error: str | None = None


def _path() -> Path:
    return Path(config.CONNECTOR_STORE_PATH).with_name("sync_state.json")


def _load() -> dict:
    path = _path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save(data: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _key(provider: Provider, source_id: str) -> str:
    return f"{provider}:{source_id}"


def get_state(provider: Provider, source_id: str) -> SourceSyncState | None:
    raw = _load().get(_key(provider, source_id))
    return SourceSyncState(**raw) if raw else None


def list_states(provider: Provider) -> list[SourceSyncState]:
    prefix = f"{provider}:"
    return [SourceSyncState(**raw) for key, raw in _load().items() if key.startswith(prefix)]


def update_state(
    provider: Provider,
    source_id: str,
    *,
    source_name: str | None = None,
    last_cursor: str | None = None,
    seen_item_ids: list[str] | None = None,
    item_count: int | None = None,
    status: str = "succeeded",
    error: str | None = None,
) -> SourceSyncState:
    with _lock:
        data = _load()
        current = data.get(_key(provider, source_id), {"provider": provider, "source_id": source_id})
        state = SourceSyncState(**current)
        state.source_name = source_name or state.source_name
        state.last_sync_at = datetime.utcnow().isoformat()
        state.last_cursor = last_cursor if last_cursor is not None else state.last_cursor
        if seen_item_ids is not None:
            state.last_seen_item_ids = list(dict.fromkeys(seen_item_ids))[-1000:]
        if item_count is not None:
            state.item_count = item_count
        state.status = status
        state.error = error
        data[_key(provider, source_id)] = state.model_dump(mode="json")
        _save(data)
        return state


def reset_state(provider: Provider, source_ids: list[str] | None = None) -> int:
    with _lock:
        data = _load()
        prefix = f"{provider}:"
        keys = [
            key
            for key in data
            if key.startswith(prefix) and (source_ids is None or key.removeprefix(prefix) in source_ids)
        ]
        for key in keys:
            data.pop(key, None)
        _save(data)
        return len(keys)


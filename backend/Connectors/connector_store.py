from __future__ import annotations

import base64
import json
import os
import secrets
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from backend import config

from .connector_schema import ConnectorAccount, ConnectorProvider, ConnectorStatus

_lock = threading.Lock()
_states: dict[str, tuple[ConnectorProvider, datetime]] = {}


def _path() -> Path:
    return Path(config.CONNECTOR_STORE_PATH)


def _xor(data: bytes) -> bytes:
    key = config.CONNECTOR_ENCRYPTION_KEY.encode("utf-8") or b"dev-only-local-key"
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))


def _protect(value: str | None) -> str | None:
    if not value:
        return None
    return base64.urlsafe_b64encode(_xor(value.encode("utf-8"))).decode("ascii")


def _unprotect(value: str | None) -> str | None:
    if not value:
        return None
    return _xor(base64.urlsafe_b64decode(value.encode("ascii"))).decode("utf-8")


def _load() -> dict[str, Any]:
    path = _path()
    if not path.exists():
        return {"accounts": {}, "status": {}, "selected_sources": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"accounts": {}, "status": {}, "selected_sources": {}}


def _save(data: dict[str, Any]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def create_oauth_state(provider: ConnectorProvider) -> str:
    state = secrets.token_urlsafe(24)
    _states[state] = (provider, datetime.utcnow())
    return state


def consume_oauth_state(state: str | None, provider: ConnectorProvider) -> bool:
    if not state:
        return False
    saved = _states.pop(state, None)
    return bool(saved and saved[0] == provider)


def save_account(account: ConnectorAccount) -> None:
    with _lock:
        data = _load()
        dumped = account.model_dump(mode="json")
        dumped["access_token"] = _protect(account.access_token)
        dumped["refresh_token"] = _protect(account.refresh_token)
        data.setdefault("accounts", {})[account.provider] = dumped
        status = data.setdefault("status", {}).get(account.provider, {})
        status.update(
            {
                "provider": account.provider,
                "status": "connected",
                "connected": True,
                "account_id": account.account_id,
                "display_name": account.display_name,
                "scopes": account.scopes,
                "error": None,
                "last_error": None,
            }
        )
        data["status"][account.provider] = status
        _save(data)


def get_account(provider: ConnectorProvider) -> ConnectorAccount | None:
    data = _load()
    raw = data.get("accounts", {}).get(provider)
    if not raw:
        return None
    safe = dict(raw)
    safe["access_token"] = _unprotect(raw.get("access_token")) or ""
    safe["refresh_token"] = _unprotect(raw.get("refresh_token"))
    return ConnectorAccount(**safe)


def delete_account(provider: ConnectorProvider) -> ConnectorStatus:
    with _lock:
        data = _load()
        data.setdefault("accounts", {}).pop(provider, None)
        data.setdefault("selected_sources", {}).pop(provider, None)
        data.setdefault("status", {})[provider] = {
            "provider": provider,
            "status": "not_connected",
            "connected": False,
            "source_counts": {},
            "items_ingested": 0,
        }
        _save(data)
    return get_status(provider)


def set_status(provider: ConnectorProvider, **updates: Any) -> ConnectorStatus:
    with _lock:
        data = _load()
        current = data.setdefault("status", {}).get(provider, {"provider": provider, "status": "not_connected"})
        current.update(updates)
        if "last_synced" in current and current["last_synced"]:
            current["last_sync_at"] = current["last_synced"]
        if "error" in current and current["error"]:
            current["last_error"] = current["error"]
        data["status"][provider] = current
        _save(data)
    return get_status(provider)


def get_status(provider: ConnectorProvider) -> ConnectorStatus:
    data = _load()
    account = get_account(provider)
    raw = data.get("status", {}).get(provider, {"provider": provider, "status": "not_connected"})
    if account:
        raw = {
            **raw,
            "provider": provider,
            "status": "connected" if raw.get("status") in (None, "not_connected") else raw.get("status"),
            "connected": True,
            "account_id": account.account_id,
            "display_name": account.display_name,
            "scopes": account.scopes,
        }
    elif provider == "github" and config.GITHUB_TOKEN:
        raw = {**raw, "provider": provider, "status": "connected", "connected": True, "display_name": "GITHUB_TOKEN"}
    elif provider == "notion" and config.NOTION_TOKEN:
        raw = {**raw, "provider": provider, "status": "connected", "connected": True, "display_name": "NOTION_TOKEN"}
    return ConnectorStatus(**raw)


def list_statuses() -> list[ConnectorStatus]:
    return [get_status(provider) for provider in ("github", "slack", "notion")]


def set_selected_sources(provider: ConnectorProvider, source_ids: list[str]) -> list[str]:
    cleaned = list(dict.fromkeys(source_id for source_id in source_ids if source_id))
    with _lock:
        data = _load()
        data.setdefault("selected_sources", {})[provider] = cleaned
        _save(data)
    return cleaned


def get_selected_sources(provider: ConnectorProvider) -> list[str]:
    data = _load()
    selected = data.get("selected_sources", {}).get(provider, [])
    return selected if isinstance(selected, list) else []

"""
Uploaded evidence provider — user-supplied evidence persisted to local JSON.

User-supplied, not live web data: items are stamped source_kind="uploaded",
is_demo_source=False, is_live_source=False.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from ..evidence_schema import EvidenceItem, EvidenceUploadRequest
from .base import EvidenceProvider, ProviderHealth, search_items

BASE_DIR = Path(__file__).resolve().parent.parent
STORE_PATH = os.getenv("UPLOADED_EVIDENCE_STORE_PATH", str(BASE_DIR / "uploaded_evidence.json"))

_lock = threading.Lock()
_items: dict[str, dict] = {}
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    if os.path.exists(STORE_PATH):
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            try:
                _items.update(json.load(f))
            except json.JSONDecodeError:
                pass
    _loaded = True


def _persist() -> None:
    os.makedirs(os.path.dirname(STORE_PATH) or ".", exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(_items, f, indent=2, default=str)


class UploadedEvidenceProvider(EvidenceProvider):
    name = "uploaded"

    def all_items(self) -> list[EvidenceItem]:
        _ensure_loaded()
        return [EvidenceItem(**data) for data in _items.values()]

    def add(self, request: EvidenceUploadRequest) -> EvidenceItem:
        _ensure_loaded()
        summary = (request.summary or request.text or "").strip()
        if not summary:
            raise ValueError("Uploaded evidence requires a 'summary' or 'text' field.")

        title = (request.title or summary[:80]).strip()
        item = EvidenceItem(
            id=f"user_{uuid.uuid4().hex[:8]}",
            domain=request.domain,
            title=title,
            summary=summary,
            source_name=request.source_name,
            source_url=request.source_url,
            published_at=request.published_at,
            evidence_type=request.evidence_type,  # defaults to user_supplied
            confidence=request.confidence,
            tags=request.tags,
            source_kind="uploaded",
            retrieved_at=datetime.utcnow().isoformat(),
            freshness_score=0.7,
            source_reliability=request.confidence,
            is_live_source=False,
            is_demo_source=False,
        )
        with _lock:
            _items[item.id] = json.loads(item.model_dump_json())
            _persist()
        return item

    def search(self, query: str | None = None, domain: str | None = None, k: int = 5) -> list[EvidenceItem]:
        return search_items(self.all_items(), query, domain, k)

    def health(self) -> ProviderHealth:
        _ensure_loaded()
        return ProviderHealth(
            provider=self.name,
            available=True,
            is_live=False,
            is_demo=False,
            item_count=len(_items),
            detail="User-uploaded evidence store (local JSON).",
        )

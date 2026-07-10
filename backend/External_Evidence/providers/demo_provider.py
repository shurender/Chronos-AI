"""
Demo evidence provider — the curated LOCAL evidence pack (demo_evidence.json).

Preserves the exact deterministic search behavior the app already relied on.
Not a live web search; every item is stamped is_demo_source=True.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..evidence_schema import EvidenceItem
from .base import EvidenceProvider, ProviderHealth, search_items

BASE_DIR = Path(__file__).resolve().parent.parent
DEMO_EVIDENCE_PATH = BASE_DIR / "demo_evidence.json"


@lru_cache(maxsize=1)
def _load() -> tuple[EvidenceItem, ...]:
    with open(DEMO_EVIDENCE_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    items = []
    for entry in raw:
        item = EvidenceItem(**entry)
        # Stamp demo provenance/quality (JSON has no source-quality fields).
        items.append(
            item.model_copy(
                update={
                    "source_kind": "demo",
                    "is_demo_source": True,
                    "is_live_source": False,
                    "source_reliability": item.confidence,
                    "freshness_score": 0.6,
                }
            )
        )
    return tuple(items)


class DemoEvidenceProvider(EvidenceProvider):
    name = "demo"

    def all_items(self) -> list[EvidenceItem]:
        return list(_load())

    def search(self, query: str | None = None, domain: str | None = None, k: int = 5) -> list[EvidenceItem]:
        return search_items(self.all_items(), query, domain, k)

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            available=True,
            is_live=False,
            is_demo=True,
            item_count=len(_load()),
            detail="Curated local demo evidence pack (no network).",
        )

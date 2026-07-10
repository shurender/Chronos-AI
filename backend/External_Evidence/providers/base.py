"""
Evidence provider abstraction.

A provider knows how to search() for evidence and report its own health().
Shared deterministic keyword/tag scoring lives here so demo and uploaded
providers rank identically. No network calls in this module.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field

from ..evidence_schema import EvidenceItem

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Common words that would otherwise cause spurious "matches" — dropped from both
# item text and query so only meaningful tokens drive scoring.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "be", "it", "this", "that", "i", "me", "my", "you", "your", "we",
    "our", "should", "would", "could", "about", "what", "how", "why", "when",
    "tell", "give", "random", "poem", "story", "if", "do", "does", "did", "can",
    "will", "at", "as", "by", "from", "into", "vs", "than", "then",
}


def tokenize(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOPWORDS}


def _score(item: EvidenceItem, query_tokens: set[str]) -> float:
    """Overlap of query tokens against tags/title/summary, lightly weighted by
    the item's own confidence so stronger evidence wins ties."""
    if not query_tokens:
        return 0.0
    tag_tokens = {t.lower() for tag in item.tags for t in _TOKEN_RE.findall(tag.lower())}
    text_tokens = tokenize(f"{item.title} {item.summary} {item.domain}")

    tag_overlap = len(query_tokens & tag_tokens)
    text_overlap = len(query_tokens & text_tokens)

    overlap = tag_overlap * 2.0 + text_overlap * 1.0
    if overlap == 0:
        return 0.0  # no token overlap -> genuinely not a match
    return overlap + item.confidence * 0.1


def search_items(
    items: list[EvidenceItem], query: str | None, domain: str | None, k: int
) -> list[EvidenceItem]:
    """Deterministic search over an in-memory item list (shared by demo/uploaded)."""
    if domain:
        domain_lc = domain.lower()
        items = [it for it in items if it.domain.lower() == domain_lc]

    query_tokens = tokenize(query or "")
    if not query_tokens:
        ranked = sorted(items, key=lambda it: it.confidence, reverse=True)
        return ranked[:k]

    scored = [(it, _score(it, query_tokens)) for it in items]
    scored = [pair for pair in scored if pair[1] > 0]
    scored.sort(key=lambda pair: (-pair[1], pair[0].id))
    return [it for it, _ in scored[:k]]


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider cannot serve a request (e.g. no API key configured)."""


class ProviderHealth(BaseModel):
    provider: str
    available: bool
    is_live: bool = False
    is_demo: bool = False
    item_count: Optional[int] = None
    detail: str = ""


class EvidenceProvider(ABC):
    name: str = "base"

    @abstractmethod
    def search(self, query: str | None = None, domain: str | None = None, k: int = 5) -> list[EvidenceItem]:
        ...

    @abstractmethod
    def health(self) -> ProviderHealth:
        ...

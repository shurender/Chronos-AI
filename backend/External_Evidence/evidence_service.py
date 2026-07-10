"""
Evidence service — loads and searches the curated local demo evidence pack.

Deterministic keyword/tag scoring (no embeddings, no network). This is a demo
evidence layer; do NOT present results as live web search.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .evidence_schema import EvidenceItem

BASE_DIR = Path(__file__).resolve().parent
DEMO_EVIDENCE_PATH = BASE_DIR / "demo_evidence.json"

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Common words that would otherwise cause spurious "matches" (e.g. an unrelated
# message sharing "a"/"about"/"the" with an evidence summary). Dropped from both
# item text and query so only meaningful tokens drive scoring.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "be", "it", "this", "that", "i", "me", "my", "you", "your", "we",
    "our", "should", "would", "could", "about", "what", "how", "why", "when",
    "tell", "give", "random", "poem", "story", "if", "do", "does", "did", "can",
    "will", "at", "as", "by", "from", "into", "vs", "than", "then",
}


def _tokenize(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOPWORDS}


@lru_cache(maxsize=1)
def _load_evidence() -> tuple[EvidenceItem, ...]:
    with open(DEMO_EVIDENCE_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return tuple(EvidenceItem(**item) for item in raw)


def get_all_evidence() -> list[EvidenceItem]:
    return list(_load_evidence())


def _score(item: EvidenceItem, query_tokens: set[str]) -> float:
    """Overlap of the query tokens against the item's tags/title/summary, lightly
    weighted by the item's own confidence so stronger evidence ranks higher on ties."""
    if not query_tokens:
        return 0.0
    tag_tokens = {t.lower() for tag in item.tags for t in _TOKEN_RE.findall(tag.lower())}
    text_tokens = _tokenize(f"{item.title} {item.summary} {item.domain}")

    tag_overlap = len(query_tokens & tag_tokens)
    text_overlap = len(query_tokens & text_tokens)

    # Tags are curated, so weight them more heavily than free-text matches.
    overlap = tag_overlap * 2.0 + text_overlap * 1.0
    if overlap == 0:
        return 0.0  # no token overlap -> genuinely not a match
    # Confidence only breaks ties between items that actually overlapped.
    return overlap + item.confidence * 0.1


def search_evidence(
    query: str | None = None, domain: str | None = None, k: int = 5
) -> list[EvidenceItem]:
    items = get_all_evidence()

    if domain:
        domain_lc = domain.lower()
        items = [it for it in items if it.domain.lower() == domain_lc]

    query_tokens = _tokenize(query or "")

    if not query_tokens:
        # No query -> return highest-confidence items (still deterministic).
        ranked = sorted(items, key=lambda it: it.confidence, reverse=True)
        return ranked[:k]

    scored = [(it, _score(it, query_tokens)) for it in items]
    scored = [pair for pair in scored if pair[1] > 0]
    # Deterministic ordering: score desc, then id asc for stable ties.
    scored.sort(key=lambda pair: (-pair[1], pair[0].id))
    return [it for it, _ in scored[:k]]

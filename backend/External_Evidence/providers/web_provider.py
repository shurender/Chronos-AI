"""Live web evidence provider backed by Tavily.

Optional by design: if TAVILY_API_KEY is missing or Tavily fails, callers catch
ProviderUnavailableError and fall back to demo/uploaded evidence. Results are
external signals, not verified facts.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

from backend import config

from ..evidence_schema import EvidenceItem
from .base import EvidenceProvider, ProviderHealth, ProviderUnavailableError, tokenize

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def _domain_from_url(url: str | None) -> str:
    if not url:
        return "web"
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.") or "web"


def _evidence_type(query: str | None, title: str, content: str):
    tokens = tokenize(" ".join([query or "", title, content]))
    if {"regulation", "regulatory", "law", "policy"} & tokens:
        return "regulatory_signal"
    if {"hiring", "job", "talent", "career"} & tokens:
        return "job_signal"
    if {"competitor", "competition"} & tokens:
        return "competitor_signal"
    if {"research", "study", "report", "paper"} & tokens:
        return "research_signal"
    return "market_signal"


def _stable_id(url: str | None, title: str, index: int) -> str:
    digest = hashlib.sha256((url or title or str(index)).encode("utf-8")).hexdigest()[:16]
    return f"tavily_{digest}"


class WebEvidenceProvider(EvidenceProvider):
    name = "tavily"

    def _configured_key(self) -> str | None:
        return config.TAVILY_API_KEY

    def search(self, query: str | None = None, domain: str | None = None, k: int = 5) -> list[EvidenceItem]:
        if not self._configured_key():
            raise ProviderUnavailableError("TAVILY_API_KEY is not set.")
        if not query:
            raise ProviderUnavailableError("Tavily search requires a non-empty query.")

        import httpx

        try:
            response = httpx.post(
                TAVILY_SEARCH_URL,
                json={
                    "api_key": self._configured_key(),
                    "query": query if not domain else f"{query} {domain}",
                    "search_depth": "basic",
                    "max_results": k,
                    "include_answer": False,
                    "include_raw_content": False,
                },
                timeout=12.0,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(f"Tavily search failed: {exc}") from exc

        retrieved_at = datetime.now(timezone.utc).isoformat()
        items: list[EvidenceItem] = []
        for idx, result in enumerate(results[:k]):
            title = str(result.get("title") or "Untitled Tavily result")
            url = result.get("url")
            summary = str(result.get("content") or result.get("snippet") or "").strip()
            result_domain = _domain_from_url(url)
            if domain and domain.lower() not in result_domain and domain.lower() not in title.lower():
                continue

            score = result.get("score")
            confidence = 0.48
            if isinstance(score, (int, float)):
                confidence = max(0.35, min(0.68, 0.35 + float(score) * 0.25))

            items.append(
                EvidenceItem(
                    id=_stable_id(url, title, idx),
                    domain=result_domain,
                    title=title,
                    summary=summary or "Tavily returned this result without a content snippet.",
                    source_name=result_domain or title,
                    source_url=url,
                    published_at=result.get("published_date"),
                    evidence_type=_evidence_type(query, title, summary),
                    confidence=round(confidence, 3),
                    tags=sorted(tokenize(f"{query or ''} {title}"))[:8],
                    source_kind="web",
                    retrieved_at=retrieved_at,
                    freshness_score=0.75,
                    source_reliability=0.55,
                    is_live_source=True,
                    is_demo_source=False,
                )
            )
        return items

    def health(self) -> ProviderHealth:
        has_key = bool(self._configured_key())
        return ProviderHealth(
            provider=self.name,
            available=has_key,
            is_live=has_key,
            is_demo=False,
            item_count=None,
            detail="TAVILY_API_KEY present; live search enabled."
            if has_key
            else "TAVILY_API_KEY missing; live web evidence will fall back to demo.",
        )

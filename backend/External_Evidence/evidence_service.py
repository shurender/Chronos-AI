"""
Evidence service — provider-orchestrating facade.

Selects an evidence provider from config.EVIDENCE_PROVIDER
(demo | uploaded | tavily/web | hybrid) and exposes the stable functions the
rest of the app already calls (search_evidence / get_all_evidence). Demo
remains the default, so existing behavior is unchanged. Live web failures fall
back to demo rather than fabricating claims.
"""

from __future__ import annotations

from backend import config
from backend.logging_config import get_logger

from .evidence_schema import EvidenceItem, EvidenceUploadRequest
from .providers.base import ProviderHealth, ProviderUnavailableError
from .providers.demo_provider import DemoEvidenceProvider
from .providers.uploaded_provider import UploadedEvidenceProvider
from .providers.web_provider import WebEvidenceProvider

logger = get_logger(__name__)

_demo = DemoEvidenceProvider()
_uploaded = UploadedEvidenceProvider()
_web = WebEvidenceProvider()


def active_provider_name() -> str:
    return (config.EVIDENCE_PROVIDER or "demo").strip().lower()


def _dedupe(items: list[EvidenceItem], k: int) -> list[EvidenceItem]:
    seen: set[str] = set()
    out: list[EvidenceItem] = []
    for it in items:
        key = (it.source_url or it.title or it.id).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out[:k]


def search_evidence(
    query: str | None = None, domain: str | None = None, k: int = 5
) -> list[EvidenceItem]:
    mode = active_provider_name()

    if mode == "uploaded":
        return _uploaded.search(query, domain, k)

    if mode in {"web", "tavily"}:
        try:
            return _web.search(query, domain, k)
        except ProviderUnavailableError as exc:
            logger.warning("Web evidence provider unavailable (%s); falling back to demo.", exc)
            return _demo.search(query, domain, k)

    if mode == "hybrid":
        combined: list[EvidenceItem] = []
        try:
            combined += _web.search(query, domain, k)
        except ProviderUnavailableError as exc:
            logger.warning("Live evidence unavailable in hybrid mode (%s); using local evidence.", exc)
        combined += _demo.search(query, domain, k)
        combined += _uploaded.search(query, domain, k)
        return _dedupe(combined, k)

    if mode != "demo":
        logger.warning("Unknown EVIDENCE_PROVIDER=%r; using demo.", mode)
    return _demo.search(query, domain, k)


def get_all_evidence() -> list[EvidenceItem]:
    """Full demo pack (backs GET /evidence). Unchanged behavior."""
    return _demo.all_items()


def add_uploaded_evidence(request: EvidenceUploadRequest) -> EvidenceItem:
    return _uploaded.add(request)


def get_provider_health() -> list[ProviderHealth]:
    return [_demo.health(), _uploaded.health(), _web.health()]

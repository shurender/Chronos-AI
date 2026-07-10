"""
FastAPI routes for the External Evidence Intelligence Layer.

Provider-backed (demo | uploaded | tavily/web | hybrid via EVIDENCE_PROVIDER). The
default demo provider is a curated LOCAL pack, not a live web search.
"""

from fastapi import APIRouter, HTTPException, Query

from .evidence_schema import (
    EvidenceItem,
    EvidenceSearchResponse,
    EvidenceUploadRequest,
)
from .evidence_service import (
    active_provider_name,
    add_uploaded_evidence,
    get_all_evidence,
    get_provider_health,
    search_evidence,
)
from .providers.base import ProviderHealth

router = APIRouter(prefix="/evidence", tags=["external-evidence"])


@router.get("/search", response_model=EvidenceSearchResponse)
def evidence_search(
    query: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    k: int = Query(default=5, ge=1, le=50),
):
    provider = active_provider_name()
    items = search_evidence(query=query, domain=domain, k=k)
    return EvidenceSearchResponse(
        query=query, domain=domain, provider=provider, isDemoPack=(provider == "demo"), items=items
    )


@router.get("/providers/health", response_model=list[ProviderHealth])
def evidence_providers_health():
    return get_provider_health()


@router.post("/upload", response_model=EvidenceItem)
def evidence_upload(request: EvidenceUploadRequest):
    """Add user-supplied evidence (JSON or raw text). Stored locally as user_supplied."""
    try:
        return add_uploaded_evidence(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("", response_model=EvidenceSearchResponse)
def evidence_all():
    return EvidenceSearchResponse(provider="demo", items=get_all_evidence())

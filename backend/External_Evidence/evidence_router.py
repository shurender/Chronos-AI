"""
FastAPI routes for the External Evidence Intelligence Layer.

Serves a curated LOCAL DEMO evidence pack (see evidence_service.py). Not a live
web search — responses are flagged isDemoPack=True.
"""

from fastapi import APIRouter, Query

from .evidence_schema import EvidenceSearchResponse
from .evidence_service import get_all_evidence, search_evidence

router = APIRouter(prefix="/evidence", tags=["external-evidence"])


@router.get("/search", response_model=EvidenceSearchResponse)
def evidence_search(
    query: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    k: int = Query(default=5, ge=1, le=50),
):
    items = search_evidence(query=query, domain=domain, k=k)
    return EvidenceSearchResponse(query=query, domain=domain, items=items)


@router.get("", response_model=EvidenceSearchResponse)
def evidence_all():
    return EvidenceSearchResponse(items=get_all_evidence())

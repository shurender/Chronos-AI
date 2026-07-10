"""FastAPI routes for provenance lookup (read-only)."""

from fastapi import APIRouter, HTTPException, Query

from . import provenance_service as service

router = APIRouter(prefix="/provenance", tags=["provenance"])


@router.get("/search")
def provenance_search(q: str = Query(...), limit: int = Query(25, ge=1, le=200)):
    return service.search(q, limit=limit)


@router.get("/source/{source_id}")
def provenance_source(source_id: str):
    source = service.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"No source found with id '{source_id}'")
    return source


@router.get("/claim/{claim_id}")
def provenance_claim(claim_id: str):
    claim = service.get_claim(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"No claim found with id '{claim_id}'")
    return claim


@router.get("/timeline/{timeline_id}")
def provenance_timeline(timeline_id: str):
    return {"timeline_id": timeline_id, "claims": service.claims_for_timeline(timeline_id)}


@router.get("/simulation/{simulation_id}")
def provenance_simulation(simulation_id: str):
    return {"simulation_id": simulation_id, "claims": service.claims_for_simulation(simulation_id)}

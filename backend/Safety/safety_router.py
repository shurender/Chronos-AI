"""
FastAPI routes for safety/privacy controls:
  POST /safety/redact           — redact PII/secrets from text
  GET  /safety/policy           — the product safety policy
  POST /data/delete-all?confirm=true          — wipe local stores
  POST /data/delete-source/{source_id}        — delete one ingested source
"""

from fastapi import APIRouter, HTTPException, Query

from backend import config

from . import policy
from .redaction import redact
from .safety_schema import PolicyResponse, RedactRequest, RedactResponse

router = APIRouter(prefix="/safety", tags=["safety"])
data_router = APIRouter(prefix="/data", tags=["data-controls"])


@router.post("/redact", response_model=RedactResponse)
def redact_text(req: RedactRequest):
    redacted, categories, count = redact(req.text)
    return RedactResponse(
        redacted_text=redacted,
        categories_detected=categories,
        redaction_count=count,
        was_redacted=count > 0,
    )


@router.get("/policy", response_model=PolicyResponse)
def get_policy():
    return PolicyResponse(
        policies=policy.POLICY_STATEMENTS,
        high_stakes_types=sorted(policy.HIGH_STAKES_TYPES),
        store_raw_unredacted=config.STORE_RAW_UNREDACTED,
        data_retention_days=config.DATA_RETENTION_DAYS,
    )


@data_router.post("/delete-all")
def delete_all(confirm: bool = Query(False)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Pass confirm=true to delete all local data.")

    cleared: dict = {}
    try:
        from backend.storage import reset_all

        reset_all()
        cleared["graph_and_vectors"] = True
    except Exception as exc:  # noqa: BLE001
        cleared["graph_and_vectors"] = f"error: {exc}"

    try:
        from backend.Provenance.provenance_service import clear_all as prov_clear

        prov_clear()
        cleared["provenance"] = True
    except Exception as exc:  # noqa: BLE001
        cleared["provenance"] = f"error: {exc}"

    try:
        from backend.Simulation.simulation_store import clear_all as sim_clear

        sim_clear()
        cleared["simulations"] = True
    except Exception as exc:  # noqa: BLE001
        cleared["simulations"] = f"error: {exc}"

    return {"deleted": True, "cleared": cleared}


@data_router.post("/delete-source/{source_id}")
def delete_source(source_id: str):
    """Delete one ingested source: its vector chunk and provenance record.
    Idempotent — returns 200 even if nothing matched."""
    removed: dict = {}
    try:
        from backend.storage import delete_chunk

        delete_chunk(source_id)
        removed["vector_chunk"] = True
    except Exception as exc:  # noqa: BLE001
        removed["vector_chunk"] = f"error: {exc}"

    try:
        from backend.Provenance.provenance_service import delete_source as prov_delete

        removed["provenance_source"] = prov_delete(source_id)
    except Exception as exc:  # noqa: BLE001
        removed["provenance_source"] = f"error: {exc}"

    return {"deleted": True, "source_id": source_id, "removed": removed}

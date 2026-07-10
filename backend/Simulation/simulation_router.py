"""FastAPI routes for persisted simulations + replay."""

from fastapi import APIRouter, HTTPException, Query

from . import simulation_store as store
from .simulation_schema import ReplayRequest, ReplayResponse

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.get("")
def list_simulations(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return {"items": store.list_all(limit=limit, offset=offset)}


@router.get("/{simulation_id}")
def get_simulation(simulation_id: str):
    stored = store.get(simulation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail=f"No simulation found with id '{simulation_id}'")
    return stored


@router.post("/{simulation_id}/replay", response_model=ReplayResponse)
def replay_simulation(simulation_id: str, request: ReplayRequest = ReplayRequest()):
    result = store.replay(simulation_id, replay_mode=request.replay_mode)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No simulation found with id '{simulation_id}'")
    return result


@router.delete("/{simulation_id}")
def delete_simulation(simulation_id: str):
    if not store.delete(simulation_id):
        raise HTTPException(status_code=404, detail=f"No simulation found with id '{simulation_id}'")
    return {"deleted": True, "simulation_id": simulation_id}

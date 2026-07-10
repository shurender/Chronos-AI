"""
FastAPI routes for the Decision Forecast simulator.

Mounted under /forecast by api.py. See forecast_engine.py for the (heuristic,
not ML-trained) methodology behind these numbers.
"""

from fastapi import APIRouter, HTTPException, Query

from .Forcast_engine import generate_forecast, generate_simulation
from .Forcast_store import (
    delete_forecast,
    get_forecast,
    list_forecasts,
    save_forecast,
)
from backend.schema import (
    DecisionForecast,
    DecisionForecastRequest,
    SimulationRequest,
    SimulationResponse,
)

router = APIRouter(prefix="/forecast", tags=["decision-forecast"])

# Mounted at the app root (no prefix) so the path is POST /simulate.
simulate_router = APIRouter(tags=["simulation"])


@simulate_router.post("/simulate", response_model=SimulationResponse)
def create_simulation(request: SimulationRequest):
    """Generate a 3-branch (or option-mapped) structured heuristic simulation and
    persist a full snapshot (evidence / twin / council / assumptions / provenance)
    so it can be retrieved and replayed. Persistence is best-effort."""
    response = generate_simulation(request)
    try:
        from backend.Simulation.simulation_store import persist_from_response

        persist_from_response(request, response)
    except Exception:  # noqa: BLE001 — persistence must never break /simulate
        pass
    return response


@router.post("/decision", response_model=DecisionForecast)
def create_decision_forecast(request: DecisionForecastRequest):
    """Generate a new decision forecast and persist it."""
    forecast = generate_forecast(request)
    save_forecast(forecast)
    return forecast


@router.get("")
def list_decision_forecasts(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """List previously generated forecasts, newest first."""
    return {"items": list_forecasts(limit=limit, offset=offset)}


@router.get("/{forecast_id}")
def get_decision_forecast(forecast_id: str):
    forecast = get_forecast(forecast_id)
    if forecast is None:
        raise HTTPException(status_code=404, detail=f"No forecast found with id '{forecast_id}'")
    return forecast


@router.delete("/{forecast_id}")
def delete_decision_forecast(forecast_id: str):
    deleted = delete_forecast(forecast_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No forecast found with id '{forecast_id}'")
    return {"deleted": True, "id": forecast_id}
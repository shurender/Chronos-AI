"""
Lightweight JSON-backed store for generated DecisionForecast objects.

Kept separate from storage.py's graph/Chroma stores since forecasts are a
different kind of artifact (simulator output, not extracted-from-evidence
graph data) — but same "save/load into a module-level dict" pattern.
"""

import json
import os
import threading

from dotenv import load_dotenv

from backend.schema import DecisionForecast

load_dotenv()

FORECAST_STORE_PATH = os.getenv("FORECAST_STORE_PATH", "./data/forecasts.json")

_lock = threading.Lock()
_forecasts: dict[str, dict] = {}
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    if os.path.exists(FORECAST_STORE_PATH):
        with open(FORECAST_STORE_PATH, "r", encoding="utf-8") as f:
            try:
                _forecasts.update(json.load(f))
            except json.JSONDecodeError:
                pass
    _loaded = True


def _persist() -> None:
    os.makedirs(os.path.dirname(FORECAST_STORE_PATH) or ".", exist_ok=True)
    with open(FORECAST_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(_forecasts, f, indent=2, default=str)


def save_forecast(forecast: DecisionForecast) -> None:
    _ensure_loaded()
    with _lock:
        _forecasts[forecast.id] = json.loads(forecast.model_dump_json())
        _persist()


def get_forecast(forecast_id: str) -> dict | None:
    _ensure_loaded()
    return _forecasts.get(forecast_id)


def list_forecasts(limit: int = 50, offset: int = 0) -> list[dict]:
    _ensure_loaded()
    items = sorted(_forecasts.values(), key=lambda f: f.get("createdAt", ""), reverse=True)
    return items[offset : offset + limit]


def delete_forecast(forecast_id: str) -> bool:
    _ensure_loaded()
    with _lock:
        if forecast_id in _forecasts:
            del _forecasts[forecast_id]
            _persist()
            return True
        return False
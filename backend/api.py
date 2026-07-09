from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # <--- ADDED THIS

from .Decision_Graph.Forcast_router import router as forecast_router
from .Memory_Vault.memory_vault_router import router as memory_vault_router
from .Decision_Graph.query_layer import (
    find_similar_past_decisions,
    get_full_graph,
    what_did_x_lead_to,
    why_did_x_fail,
)
from backend.storage import load_graph

app = FastAPI(title="Decision Graph API")

# --- ADDED CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],
)
# --------------------------------

load_graph()

app.include_router(forecast_router)
app.include_router(memory_vault_router)

@app.get("/graph")
def graph():
    return get_full_graph()

@app.get("/query/similar")
def similar(q: str, k: int = 5):
    return find_similar_past_decisions(q, k=k)

@app.get("/query/why-failed")
def why_failed(label: str):
    result = why_did_x_fail(label)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No node found with label '{label}'")
    return result

@app.get("/query/led-to")
def led_to(label: str):
    result = what_did_x_lead_to(label)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No node found with label '{label}'")
    return result
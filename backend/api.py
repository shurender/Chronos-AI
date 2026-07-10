import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .logging_config import RequestIdMiddleware, get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

from .Decision_Graph.Forcast_router import router as forecast_router
from .Decision_Graph.Forcast_router import simulate_router
from .Digital_Twin.digital_twin_router import router as digital_twin_router
from .External_Evidence.evidence_router import router as evidence_router
from .Future_Self.avatar_router import router as avatar_router
from .Ingestion.ingestion_router import router as ingestion_router
from .Intake.intake_router import router as intake_router
from .LLM.llm_router import router as llm_router
from .Memory_Vault.memory_vault_router import router as memory_vault_router
from .Provenance.provenance_router import router as provenance_router
from .Safety.safety_router import data_router, router as safety_router
from .Simulation.simulation_router import router as simulations_router
from .Decision_Graph.query_layer import (
    find_similar_past_decisions_clean,
    get_full_graph,
    what_did_x_lead_to,
    why_did_x_fail,
)
from backend.storage import load_graph

app = FastAPI(title="Decision Graph API")

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,  # override via CORS_ORIGINS env var; avoid "*" beyond local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(
    "Starting Decision Graph API (demo_mode=%s, llm_provider=%s, evidence_provider=%s, cors_origins=%s)",
    config.DEMO_MODE,
    config.LLM_PROVIDER,
    config.EVIDENCE_PROVIDER,
    config.CORS_ORIGINS,
)

load_graph()


def _warm_embeddings() -> None:
    """Load the embedding model in the background at startup so the FIRST
    /simulate (which triggers the twin + precedent lookup) isn't slowed by a
    cold model load (~20s). Best-effort — never blocks startup."""
    try:
        from backend.LLM.llm_service import embed_text

        embed_text("warmup")
        logger.info("Embedding model warmed up.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embedding warmup skipped: %s", exc)


threading.Thread(target=_warm_embeddings, daemon=True).start()

app.include_router(forecast_router)
app.include_router(simulate_router)
app.include_router(digital_twin_router)
app.include_router(evidence_router)
app.include_router(avatar_router)
app.include_router(ingestion_router)
app.include_router(intake_router)
app.include_router(llm_router)
app.include_router(memory_vault_router)
app.include_router(provenance_router)
app.include_router(simulations_router)
app.include_router(safety_router)
app.include_router(data_router)

@app.get("/graph")
def graph():
    return get_full_graph()

@app.get("/query/similar")
def similar(q: str, k: int = 5):
    return find_similar_past_decisions_clean(q, k=k)

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


# --- Health / readiness --------------------------------------------------------
def _storage_writable() -> dict:
    import os
    import tempfile

    directory = os.path.dirname(config.CHROMA_PATH) or "."
    try:
        os.makedirs(directory, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=directory, delete=True):
            pass
        return {"writable": True, "path": directory}
    except Exception as exc:  # noqa: BLE001
        return {"writable": False, "path": directory, "error": str(exc)}


def _dependency_report() -> dict:
    report: dict = {"app_import": True}

    try:
        from backend import storage

        report["graph"] = {
            "loaded": True,
            "nodes": storage.G.number_of_nodes(),
            "edges": storage.G.number_of_edges(),
        }
    except Exception as exc:  # noqa: BLE001
        report["graph"] = {"loaded": False, "error": str(exc)}

    try:
        from backend.External_Evidence.evidence_service import active_provider_name, get_provider_health

        report["evidence_provider"] = {
            "active": active_provider_name(),
            "providers": [p.model_dump() for p in get_provider_health()],
        }
    except Exception as exc:  # noqa: BLE001
        report["evidence_provider"] = {"error": str(exc)}

    try:
        from backend.LLM.llm_service import health as llm_health

        report["llm_provider"] = llm_health()
    except Exception as exc:  # noqa: BLE001
        report["llm_provider"] = {"error": str(exc)}

    report["storage"] = _storage_writable()
    report["demo_mode"] = config.DEMO_MODE
    return report


@app.get("/health")
def health():
    """Liveness — the app process is up."""
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    """Readiness — graph is loaded and storage is writable."""
    deps = _dependency_report()
    ready = bool(deps.get("graph", {}).get("loaded")) and bool(deps.get("storage", {}).get("writable"))
    if not ready:
        raise HTTPException(status_code=503, detail={"ready": False, "dependencies": deps})
    return {"ready": True}


@app.get("/health/dependencies")
def health_dependencies():
    """Detailed dependency report: graph, evidence provider, LLM provider, storage."""
    return _dependency_report()
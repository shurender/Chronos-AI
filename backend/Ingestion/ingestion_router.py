"""
FastAPI routes for API-driven ingestion.

Synchronous by design (see ingestion_service.py). Failed runs are still
persisted (GET /ingest/runs/{run_id} shows them) but the POST call itself
returns a non-2xx with a clear error — failures are surfaced, not swallowed.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from . import ingestion_service as service
from .ingestion_schema import IngestGithubRequest, IngestionRun, IngestResetResponse

router = APIRouter(prefix="/ingest", tags=["ingestion"])


def _respond(run: IngestionRun) -> IngestionRun:
    if run.status == "failed":
        raise HTTPException(
            status_code=502,
            detail={
                "run_id": run.run_id,
                "errors": run.errors or ["Ingestion failed for an unknown reason."],
                "warnings": run.warnings,
                "files_received": run.files_received,
                "files_parsed": run.files_parsed,
                "files_failed": run.files_failed,
            },
        )
    return run


@router.post("/demo", response_model=IngestionRun)
def ingest_demo():
    """Parse the bundled demo GitHub/Slack/Notion/PDF sources and build the graph."""
    return _respond(service.ingest_demo())


@router.post("/github", response_model=IngestionRun)
def ingest_github(request: IngestGithubRequest):
    """Ingest public commits/issues from a GitHub repo (no OAuth; optional GITHUB_TOKEN)."""
    return _respond(service.ingest_github(request))


@router.post("/upload", response_model=IngestionRun)
def ingest_upload(files: list[UploadFile] = File(...)):
    """Ingest uploaded files (.pdf, .md/.markdown, .json)."""
    return _respond(service.ingest_upload(files))


@router.get("/runs")
def list_runs(limit: int = 50, offset: int = 0):
    return {"items": service.list_runs(limit=limit, offset=offset)}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No ingestion run found with id '{run_id}'")
    return run


@router.post("/reset", response_model=IngestResetResponse)
def reset(confirm: bool = False):
    if not confirm:
        raise HTTPException(status_code=400, detail="Pass confirm=true to reset graph/vector data.")
    nodes_before, edges_before = service.reset_all()
    return IngestResetResponse(reset=True, nodes_before=nodes_before, edges_before=edges_before)

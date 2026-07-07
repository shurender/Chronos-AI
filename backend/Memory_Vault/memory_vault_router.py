"""
FastAPI routes for the Memory Vault feature.

Mounted under /memory by api.py. Nothing to generate or persist here — the
Decision Graph and Timeline Accordion are both read-only views derived live
from the extraction graph (storage.py's G) built by extraction_pipeline.py.
See memory_vault_engine.py.
"""

from fastapi import APIRouter, Query

from .memory_vault_engine import build_memory_vault
from backend.schema import MemoryVaultResponse

router = APIRouter(prefix="/memory", tags=["memory-vault"])


@router.get("/vault", response_model=MemoryVaultResponse)
def get_memory_vault(
    current_year: int = Query(2026, ge=1900, le=3000),
    max_decisions: int = Query(4, ge=1, le=20),
):
    return build_memory_vault(current_year=current_year, max_decisions=max_decisions)
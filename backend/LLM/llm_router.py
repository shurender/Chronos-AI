"""FastAPI route exposing LLM/embedding provider health."""

from fastapi import APIRouter

from . import llm_service

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/health")
def llm_health():
    return llm_service.health()

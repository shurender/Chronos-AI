"""FastAPI route for the Clarifying Intake Agent."""

from fastapi import APIRouter

from .intake_schema import IntakeAnalysis, IntakeAnalyzeRequest
from .intake_service import analyze_intake

router = APIRouter(prefix="/intake", tags=["intake"])


@router.post("/analyze", response_model=IntakeAnalysis)
def analyze(request: IntakeAnalyzeRequest):
    """Detect missing decision context and produce targeted clarifying questions."""
    return analyze_intake(request)

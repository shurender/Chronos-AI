"""FastAPI routes for the Digital Twin Constructor."""

from fastapi import APIRouter, HTTPException

from .digital_twin_schema import DigitalTwinBuildRequest, DigitalTwinProfile
from .digital_twin_service import build_digital_twin, get_profile

router = APIRouter(prefix="/digital-twin", tags=["digital-twin"])


@router.post("/build", response_model=DigitalTwinProfile)
def build(request: DigitalTwinBuildRequest = DigitalTwinBuildRequest()):
    return build_digital_twin(request)


@router.get("/{profile_id}")
def get(profile_id: str):
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No digital twin profile found with id '{profile_id}'")
    return profile

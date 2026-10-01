from fastapi import APIRouter

from backend.schemas import CategoriesResponse, HealthResponse, ProviderInfo, SEVERITIES
from construction_hazards import config
from construction_hazards.schema import CATEGORIES

router = APIRouter(prefix="/api", tags=["info"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", providers={
        "claude": ProviderInfo(available=config.CLAUDE_AVAILABLE, model=config.CLAUDE_MODEL, effort=config.CLAUDE_EFFORT),
        "domo": ProviderInfo(available=config.DOMO_AVAILABLE, model=config.DOMO_MODEL),
    })


@router.get("/categories", response_model=CategoriesResponse)
def categories() -> CategoriesResponse:
    """The 39 hazard categories and 3 severities the analyzer can return."""
    return CategoriesResponse(categories=list(CATEGORIES), severities=list(SEVERITIES))

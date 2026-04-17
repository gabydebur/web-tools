"""Health and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def ready(settings: Settings = Depends(get_settings)) -> HealthResponse:
    # Touch the config to ensure it was parsed; further checks could ping SearxNG.
    _ = settings.searxng_base_url
    return HealthResponse(status="ok")

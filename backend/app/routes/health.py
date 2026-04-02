"""Health-check route."""
from __future__ import annotations

from fastapi import APIRouter

import yt_dlp

from app.models.schemas import HealthResponse

router = APIRouter()

_VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    """Returns service health and dependency versions."""
    return HealthResponse(
        status="ok",
        version=_VERSION,
        yt_dlp_version=yt_dlp.version.__version__,
    )

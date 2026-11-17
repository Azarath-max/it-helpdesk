from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.db import check_database
from app.core.errors import AppError

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    """Liveness response."""

    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    """Readiness response."""

    status: Literal["ready"] = "ready"


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
def health() -> HealthResponse:
    """Report that the API process is running."""
    return HealthResponse()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness check",
    responses={503: {"description": "PostgreSQL is not reachable"}},
)
def ready() -> ReadyResponse:
    """Report that the API can reach PostgreSQL."""
    try:
        check_database()
    except Exception as exc:
        raise AppError(
            "NOT_READY",
            "Database is not reachable",
            status_code=503,
        ) from exc
    return ReadyResponse()

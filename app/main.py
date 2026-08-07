"""FastAPI application entrypoint.

Wires together settings, logging, and the versioned API router.
Middleware and centralized exception handlers are still stubbed with
TODOs (see `app/core/middleware.py`, `app/core/exceptions.py`) and are
Phase 5 - Observability work.

See IMPLEMENTATION_PLAN.md Section 8 (Phase 1 - Project Skeleton) and
Section 7 (Folder Structure).
"""
from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings)
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Application factory.

    Kept as a factory (rather than a bare module-level app built inline)
    so tests can construct fresh app instances with overridden
    dependencies.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
    )

    # TODO: register correlation-id/request-logging middleware
    # (see app/core/middleware.py - not yet implemented).

    # TODO: register centralized exception handlers
    # (see app/core/exceptions.py - not yet implemented; routers
    # currently map DomainError -> HTTPException locally as an interim
    # measure, see app/api/v1/appointments.py and availability.py).

    app.include_router(api_v1_router, prefix="/api/v1")

    # TODO: add GET /health (liveness + DB connectivity probe, see
    # IMPLEMENTATION_PLAN.md Section 10) - Phase 5 work.

    return app


app = create_app()

logger.info("app_configured", environment=settings.environment)


"""FastAPI application entrypoint.

Wires together settings, logging, the correlation-id/request-logging
middleware, centralized exception handlers, and the versioned API
router (IMPLEMENTATION_PLAN.md Section 8 Phase 1, Section 12
Observability).
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import CorrelationIdMiddleware
from app.db.session import SessionLocal

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

    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app)

    app.include_router(api_v1_router, prefix="/api/v1")

    @app.get("/health")
    def health() -> dict:
        """Liveness + DB connectivity probe (Section 10). Deliberately
        bypasses the repository/service layers - this is an infra-only
        check, not a domain operation - and uses its own short-lived
        session rather than the request-scoped `get_db` dependency.
        """
        db_status = "UP"
        try:
            db = SessionLocal()
            try:
                db.execute(text("SELECT 1"))
            finally:
                db.close()
        except Exception:
            logger.exception("health_check_db_failed")
            db_status = "DOWN"

        payload = {"status": db_status, "database": db_status, "version": settings.version}
        if db_status == "DOWN":
            return JSONResponse(status_code=503, content=payload)
        return payload

    return app


app = create_app()

logger.info("app_configured", environment=settings.environment)


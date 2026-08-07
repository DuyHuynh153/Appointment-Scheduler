"""Correlation ID + structured request logging middleware (ADR-003,
IMPLEMENTATION_PLAN.md Section 12).
"""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Reads/generates `X-Correlation-ID`, generates a fresh
    `request_id` per request, binds both to `structlog.contextvars` and
    `request.state` (so exception handlers can read the correlation id
    too), echoes the header back, and emits one structured access log
    line per request (ADR-003).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        header_name = settings.correlation_id_header

        correlation_id = request.headers.get(header_name) or str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        request.state.correlation_id = correlation_id
        request.state.request_id = request_id

        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_id=request_id,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers[header_name] = correlation_id

        logger.info(
            "request_handled",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            user_agent=request.headers.get("user-agent"),
            response_size=response.headers.get("content-length"),
            correlation_id=correlation_id,
            request_id=request_id,
        )

        return response

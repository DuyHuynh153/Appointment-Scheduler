"""Domain exception types + centralized exception handlers.

The domain exception hierarchy below is raised by the service layer
(`app/services/`) and is framework-agnostic - it knows nothing about
FastAPI/HTTP status codes. `register_exception_handlers()` wires these
(and FastAPI/Starlette's own exception types) to the standardized error
response shape `{"code", "message", "correlation_id"}` described in
IMPLEMENTATION_PLAN.md Section 12 - see `app/main.py` for registration.
"""
from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger(__name__)


class DomainError(Exception):
    """Base class for all framework-agnostic domain errors.

    `code` is a short machine-readable identifier (future API layer
    maps it to an HTTP status); `message` is human-readable.
    """

    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """Raised when a referenced entity (dealer, vehicle, service type,
    appointment, ...) does not exist."""

    code = "not_found"


class ValidationError(DomainError):
    """Raised for request-shape/business-rule validation failures that
    are the caller's fault (dealer mismatch, outside business hours,
    missing required fields, ...)."""

    code = "validation_error"


class ConflictError(DomainError):
    """Raised when the requested booking cannot be satisfied due to a
    state conflict (no technician/bay available, overlap, already
    cancelled, ...)."""

    code = "conflict"


_DOMAIN_ERROR_STATUS_CODES: dict[type[DomainError], int] = {
    NotFoundError: 404,
    ValidationError: 422,
    ConflictError: 409,
}


def domain_error_status_code(exc: DomainError) -> int:
    """Maps a `DomainError` (sub)type to its HTTP status code."""
    return _DOMAIN_ERROR_STATUS_CODES.get(type(exc), 500)


def _correlation_id(request: Request) -> str:
    """Reads the correlation id bound onto `request.state` by
    `CorrelationIdMiddleware` (see `app/core/middleware.py`). Falls back
    to `"unknown"` so handlers never fail if a request somehow reaches
    here without the middleware having run (e.g. in isolated tests)."""
    return getattr(request.state, "correlation_id", None) or "unknown"


def _error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    """Builds the standardized error envelope (Section 12):
    `{"code", "message", "correlation_id"}`."""
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "correlation_id": _correlation_id(request)},
    )


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return _error_response(request, domain_error_status_code(exc), exc.code, exc.message)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles FastAPI/Pydantic request validation failures (422), e.g.
    a malformed body, an unknown field (`extra="forbid"`), or a naive/
    ambiguous `start_time` rejected by `to_utc()`."""
    details = "; ".join(
        f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}" for error in exc.errors()
    )
    return _error_response(request, 422, "validation_error", details or "Request validation failed.")


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles Starlette/FastAPI's own `HTTPException` (e.g. 404 for an
    unknown route, 405 for a wrong method) with the standardized
    envelope instead of Starlette's default `{"detail": ...}` shape."""
    return _error_response(request, exc.status_code, "http_error", str(exc.detail))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler: logs the full exception server-side but
    never leaks internals (stack trace, exception message) to the
    client (Section 12)."""
    logger.exception("unhandled_exception", path=request.url.path, method=request.method)
    return _error_response(request, 500, "internal_error", "An unexpected error occurred.")


def register_exception_handlers(app: FastAPI) -> None:
    """Registers all centralized exception handlers on `app` (called
    once from `app/main.py`). Order does not matter to FastAPI/Starlette
    - it dispatches by the most specific matching exception type."""
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


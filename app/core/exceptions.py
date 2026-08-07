"""Domain exception types + centralized exception handler.

The domain exception hierarchy below is raised by the service layer
(`app/services/`) and is framework-agnostic - it knows nothing about
FastAPI/HTTP status codes. Mapping these to the standardized error
response shape `{"code", "message", "correlation_id"}` and registering
the actual FastAPI exception handler is Phase 5 - Observability work
and is intentionally NOT implemented yet (see TODO below); only the
exception types needed by `BookingService` exist so far.
"""


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
    """Maps a `DomainError` (sub)type to its HTTP status code.

    This is a narrow, router-level convenience only - it does NOT
    build the full standardized `{"code", "message", "correlation_id"}`
    envelope described in IMPLEMENTATION_PLAN.md Section 12. That
    envelope requires the correlation ID (from middleware) and is
    deliberately deferred to Phase 5 - Observability, where a real
    centralized FastAPI exception handler will be registered on
    `app/main.py` and this helper can be removed/absorbed into it.
    """
    return _DOMAIN_ERROR_STATUS_CODES.get(type(exc), 500)


# TODO (Phase 5 - Observability, see IMPLEMENTATION_PLAN.md Section 12):
# - Register a centralized exception handler on the FastAPI app (see
#   `app/main.py`) that maps `DomainError` subclasses (and any
#   unhandled exception) to the standardized error response shape:
#       {"code": "...", "message": "...", "correlation_id": "..."}
# - Ensure unhandled exceptions never leak a stack trace to the client.
# - Once that handler exists, routers should stop catching DomainError
#   themselves (see app/api/v1/appointments.py, availability.py) and
#   let it propagate to the centralized handler instead.


"""Pydantic request/response DTOs (API contract).

Kept separate from ORM models on purpose - see `app/models/` and
IMPLEMENTATION_PLAN.md Section 7.

`error.py` (standardized `{"code", "message", "correlation_id"}` error
shape) is deferred to Phase 5 - Observability, since it needs the
correlation ID produced by the not-yet-implemented middleware.
"""
from app.schemas.appointment import AppointmentCreateRequest, AppointmentResponse
from app.schemas.availability import AvailabilityResponse, AvailabilitySlotResponse

__all__ = [
    "AppointmentCreateRequest",
    "AppointmentResponse",
    "AvailabilityResponse",
    "AvailabilitySlotResponse",
]


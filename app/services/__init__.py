"""Business logic layer (framework-agnostic, unit-testable - see ADR-002).

`BookingService` (see `app/services/booking.py`) owns the booking use
case's transaction boundary: validate -> assign technician/bay ->
re-check availability with `SELECT ... FOR UPDATE` -> check overlap ->
insert (ADR-005 and its amendment for vehicle locking).

TODO: `AvailabilityService` (or a method on `BookingService`) to
compute open slots for `GET /api/v1/availability` - not implemented
yet.
"""
from app.services.availability import AvailabilityService
from app.services.booking import BookingService

__all__ = ["AvailabilityService", "BookingService"]


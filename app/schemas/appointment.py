"""Pydantic DTOs for the Appointment resource (IMPLEMENTATION_PLAN.md
Section 10). Kept separate from `app.models.appointment` on purpose
(Section 7) so API contracts and DB shape can evolve independently.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.appointment import AppointmentStatus
from app.utils.time import to_utc


class AppointmentCreateRequest(BaseModel):
    """Request body for `POST /api/v1/appointments`.

    `technician_id`/`bay_id` are deliberately NOT fields here: the
    contract says the backend always assigns them, and unknown fields
    are rejected (`extra="forbid"`) so a client attempting to send
    them gets an explicit `422` instead of having the value silently
    ignored (Section 10).

    `notes` is intentionally omitted - see IMPLEMENTATION_PLAN.md's
    open issue: there is no corresponding database column yet.

    `start_time` must be timezone-aware; it is normalized to UTC here
    (single point of entry) so no naive/ambiguous timestamp ever
    reaches `BookingService` (IMPLEMENTATION_PLAN.md Section 4: "all
    timestamps stored/compared in UTC").
    """

    model_config = ConfigDict(extra="forbid")

    dealer_id: uuid.UUID
    vehicle_id: uuid.UUID
    service_type_id: uuid.UUID
    start_time: datetime

    @field_validator("start_time")
    @classmethod
    def _normalize_start_time_to_utc(cls, value: datetime) -> datetime:
        try:
            return to_utc(value)
        except ValueError as exc:
            raise ValueError(
                "start_time must be timezone-aware (e.g. include a UTC offset or 'Z' suffix)."
            ) from exc


class AppointmentResponse(BaseModel):
    """Response body for all appointment endpoints - the "full
    appointment object" required by Section 10 (id, assigned
    technician, assigned bay, computed end_time, status)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dealer_id: uuid.UUID
    vehicle_id: uuid.UUID
    service_type_id: uuid.UUID
    technician_id: uuid.UUID
    bay_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime

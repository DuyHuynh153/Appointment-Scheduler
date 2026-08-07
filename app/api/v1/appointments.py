"""`/appointments` endpoints (IMPLEMENTATION_PLAN.md Section 10).

HTTP concerns only: parse request -> call `BookingService` -> serialize
response. Business logic and the transaction boundary live in
`BookingService`, not here (Section 5/7).

Domain exceptions are caught here and mapped to plain `HTTPException`s
via `domain_error_status_code` - a temporary, router-local mapping.
The standardized `{"code", "message", "correlation_id"}` error body is
Phase 5 - Observability work (see `app/core/exceptions.py`).
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_booking_service
from app.core.exceptions import DomainError, domain_error_status_code
from app.models.appointment import AppointmentStatus
from app.schemas.appointment import AppointmentCreateRequest, AppointmentResponse
from app.services.booking import BookingService

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreateRequest,
    service: BookingService = Depends(get_booking_service),
) -> AppointmentResponse:
    try:
        appointment = service.create_appointment(
            dealer_id=payload.dealer_id,
            vehicle_id=payload.vehicle_id,
            service_type_id=payload.service_type_id,
            start_time=payload.start_time,
        )
    except DomainError as exc:
        raise HTTPException(status_code=domain_error_status_code(exc), detail=exc.message) from exc
    return AppointmentResponse.model_validate(appointment)


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    dealer_id: uuid.UUID = Query(..., description="Required - scopes the listing to one dealer."),
    appointment_date: date | None = Query(None, alias="date"),
    technician_id: uuid.UUID | None = Query(None),
    status_: AppointmentStatus | None = Query(None, alias="status"),
    service: BookingService = Depends(get_booking_service),
) -> list[AppointmentResponse]:
    try:
        appointments = service.list_appointments(
            dealer_id,
            appointment_date=appointment_date,
            technician_id=technician_id,
            status=status_,
        )
    except DomainError as exc:
        raise HTTPException(status_code=domain_error_status_code(exc), detail=exc.message) from exc
    return [AppointmentResponse.model_validate(a) for a in appointments]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: uuid.UUID,
    service: BookingService = Depends(get_booking_service),
) -> AppointmentResponse:
    try:
        appointment = service.get_appointment(appointment_id)
    except DomainError as exc:
        raise HTTPException(status_code=domain_error_status_code(exc), detail=exc.message) from exc
    return AppointmentResponse.model_validate(appointment)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(
    appointment_id: uuid.UUID,
    service: BookingService = Depends(get_booking_service),
) -> None:
    try:
        service.cancel_appointment(appointment_id)
    except DomainError as exc:
        raise HTTPException(status_code=domain_error_status_code(exc), detail=exc.message) from exc

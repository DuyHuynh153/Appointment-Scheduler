"""`/appointments` endpoints (IMPLEMENTATION_PLAN.md Section 10).

HTTP concerns only: parse request -> call `BookingService` -> serialize
response. Business logic and the transaction boundary live in
`BookingService`, not here (Section 5/7).

Domain exceptions (`DomainError` subclasses) are not caught here - they
propagate to the centralized exception handlers registered in
`app/main.py` (see `app/core/exceptions.py`), which build the
standardized `{"code", "message", "correlation_id"}` error body.
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_booking_service
from app.models.appointment import AppointmentStatus
from app.schemas.appointment import AppointmentCreateRequest, AppointmentResponse
from app.services.booking import BookingService

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreateRequest,
    service: BookingService = Depends(get_booking_service),
) -> AppointmentResponse:
    appointment = service.create_appointment(
        dealer_id=payload.dealer_id,
        vehicle_id=payload.vehicle_id,
        service_type_id=payload.service_type_id,
        start_time=payload.start_time,
    )
    return AppointmentResponse.model_validate(appointment)


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    dealer_id: uuid.UUID = Query(..., description="Required - scopes the listing to one dealer."),
    appointment_date: date | None = Query(None, alias="date"),
    technician_id: uuid.UUID | None = Query(None),
    status_: AppointmentStatus | None = Query(None, alias="status"),
    service: BookingService = Depends(get_booking_service),
) -> list[AppointmentResponse]:
    appointments = service.list_appointments(
        dealer_id,
        appointment_date=appointment_date,
        technician_id=technician_id,
        status=status_,
    )
    return [AppointmentResponse.model_validate(a) for a in appointments]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: uuid.UUID,
    service: BookingService = Depends(get_booking_service),
) -> AppointmentResponse:
    appointment = service.get_appointment(appointment_id)
    return AppointmentResponse.model_validate(appointment)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(
    appointment_id: uuid.UUID,
    service: BookingService = Depends(get_booking_service),
) -> None:
    service.cancel_appointment(appointment_id)

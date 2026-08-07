"""`/availability` endpoint (IMPLEMENTATION_PLAN.md Section 10)."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_availability_service
from app.core.exceptions import DomainError, domain_error_status_code
from app.schemas.availability import AvailabilityResponse, AvailabilitySlotResponse
from app.services.availability import AvailabilityService

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("", response_model=AvailabilityResponse)
def get_availability(
    dealer_id: uuid.UUID = Query(...),
    service_type_id: uuid.UUID = Query(...),
    target_date: date = Query(..., alias="date"),
    service: AvailabilityService = Depends(get_availability_service),
) -> AvailabilityResponse:
    try:
        slots = service.get_availability(
            dealer_id=dealer_id,
            service_type_id=service_type_id,
            target_date=target_date,
        )
    except DomainError as exc:
        raise HTTPException(status_code=domain_error_status_code(exc), detail=exc.message) from exc
    return AvailabilityResponse(
        slots=[AvailabilitySlotResponse.model_validate(s) for s in slots]
    )

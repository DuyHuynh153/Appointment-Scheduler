"""`/availability` endpoint (IMPLEMENTATION_PLAN.md Section 10).

Domain exceptions propagate to the centralized handlers in
`app/main.py`/`app/core/exceptions.py`.
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_availability_service
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
    slots = service.get_availability(
        dealer_id=dealer_id,
        service_type_id=service_type_id,
        target_date=target_date,
    )
    return AvailabilityResponse(
        slots=[AvailabilitySlotResponse.model_validate(s) for s in slots]
    )

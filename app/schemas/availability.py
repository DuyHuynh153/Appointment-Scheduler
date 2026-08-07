"""Pydantic DTOs for `GET /api/v1/availability` (IMPLEMENTATION_PLAN.md
Section 10)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AvailabilitySlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_time: datetime
    end_time: datetime
    available_technicians: int
    available_bays: int


class AvailabilityResponse(BaseModel):
    slots: list[AvailabilitySlotResponse]

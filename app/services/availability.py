"""AvailabilityService - read-only slot/resource-availability query
for `GET /availability` (IMPLEMENTATION_PLAN.md Section 10).

Framework-agnostic like `BookingService`; depends only on a `Session`
and repositories. Does not lock rows or mutate anything - this is a
pure read used to help a client pick a `start_time` before calling
`POST /appointments`, so it deliberately does NOT hold the same
row-locking guarantees as the booking flow (see ADR-005): the actual
no-overlap invariant is only enforced at booking time.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.repositories.appointment import AppointmentRepository
from app.repositories.dealer import DealerRepository
from app.repositories.service_bay import ServiceBayRepository
from app.repositories.service_type import ServiceTypeRepository
from app.repositories.technician import TechnicianRepository
from app.utils.time import parse_hhmm


@dataclass(frozen=True)
class AvailabilitySlot:
    start_time: datetime
    end_time: datetime
    available_technicians: int
    available_bays: int


class AvailabilityService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

        self.dealers = DealerRepository(db)
        self.service_types = ServiceTypeRepository(db)
        self.technicians = TechnicianRepository(db)
        self.bays = ServiceBayRepository(db)
        self.appointments = AppointmentRepository(db)

    def get_availability(
        self,
        *,
        dealer_id: uuid.UUID,
        service_type_id: uuid.UUID,
        target_date: date,
    ) -> list[AvailabilitySlot]:
        if self.dealers.get_by_id(dealer_id) is None:
            raise NotFoundError(f"Dealer {dealer_id} not found.")

        service_type = self.service_types.get_by_id(service_type_id)
        if service_type is None:
            raise NotFoundError(f"Service type {service_type_id} not found.")

        duration = timedelta(minutes=service_type.duration_minutes)
        hours_start = parse_hhmm(self.settings.business_hours_start)
        hours_end = parse_hhmm(self.settings.business_hours_end)

        technicians = self.technicians.list_by_dealer(dealer_id)
        bays = self.bays.list_by_dealer(dealer_id)

        slots: list[AvailabilitySlot] = []
        slot_start = datetime.combine(target_date, hours_start, tzinfo=timezone.utc)
        day_end = datetime.combine(target_date, hours_end, tzinfo=timezone.utc)

        while slot_start + duration <= day_end:
            slot_end = slot_start + duration

            available_technicians = sum(
                1
                for t in technicians
                if not self.appointments.has_technician_overlap(t.id, slot_start, slot_end)
            )
            available_bays = sum(
                1
                for b in bays
                if not self.appointments.has_bay_overlap(b.id, slot_start, slot_end)
            )

            slots.append(
                AvailabilitySlot(
                    start_time=slot_start,
                    end_time=slot_end,
                    available_technicians=available_technicians,
                    available_bays=available_bays,
                )
            )
            slot_start = slot_end

        return slots

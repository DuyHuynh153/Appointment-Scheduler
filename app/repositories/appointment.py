"""Appointment repository - persistence access only.

Overlap *queries* live here because they are pure SQLAlchemy (no
decision-making): they answer "does an active appointment already
occupy this technician/bay/vehicle during this window?" using the
half-open `[start_time, end_time)` semantics documented on the
`Appointment` model. Deciding *what to do* with that answer (reject
the booking, pick another candidate, etc.) and owning the transaction/
locking around it belongs to the future `BookingService`, not to this
repository (see IMPLEMENTATION_PLAN.md Section 7 and ADR-005).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Select, func, select

from app.models.appointment import Appointment, AppointmentStatus
from app.repositories.base import BaseRepository

# Overlap checks only consider appointments in this set of "active"
# statuses; a CANCELLED appointment no longer occupies the resource.
_ACTIVE_STATUSES = (AppointmentStatus.SCHEDULED,)


class AppointmentRepository(BaseRepository[Appointment]):
    model = Appointment

    def list_by_dealer(
        self,
        dealer_id: uuid.UUID,
        *,
        appointment_date: date | None = None,
        technician_id: uuid.UUID | None = None,
        status: AppointmentStatus | None = None,
    ) -> list[Appointment]:
        stmt: Select = select(Appointment).where(Appointment.dealer_id == dealer_id)
        if appointment_date is not None:
            stmt = stmt.where(func.date(Appointment.start_time) == appointment_date)
        if technician_id is not None:
            stmt = stmt.where(Appointment.technician_id == technician_id)
        if status is not None:
            stmt = stmt.where(Appointment.status == status)
        return list(self.db.scalars(stmt).all())

    def has_technician_overlap(
        self,
        technician_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        *,
        exclude_appointment_id: uuid.UUID | None = None,
    ) -> bool:
        return self._has_overlap(
            Appointment.technician_id == technician_id,
            start_time,
            end_time,
            exclude_appointment_id=exclude_appointment_id,
        )

    def has_bay_overlap(
        self,
        bay_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        *,
        exclude_appointment_id: uuid.UUID | None = None,
    ) -> bool:
        return self._has_overlap(
            Appointment.bay_id == bay_id,
            start_time,
            end_time,
            exclude_appointment_id=exclude_appointment_id,
        )

    def has_vehicle_overlap(
        self,
        vehicle_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        *,
        exclude_appointment_id: uuid.UUID | None = None,
    ) -> bool:
        return self._has_overlap(
            Appointment.vehicle_id == vehicle_id,
            start_time,
            end_time,
            exclude_appointment_id=exclude_appointment_id,
        )

    def _has_overlap(
        self,
        resource_filter,
        start_time: datetime,
        end_time: datetime,
        *,
        exclude_appointment_id: uuid.UUID | None,
    ) -> bool:
        """Half-open interval overlap: existing.start < new.end AND
        existing.end > new.start (see Appointment model docstring)."""
        stmt = (
            select(Appointment.id)
            .where(resource_filter)
            .where(Appointment.status.in_(_ACTIVE_STATUSES))
            .where(Appointment.start_time < end_time)
            .where(Appointment.end_time > start_time)
        )
        if exclude_appointment_id is not None:
            stmt = stmt.where(Appointment.id != exclude_appointment_id)
        return self.db.scalars(stmt.limit(1)).first() is not None

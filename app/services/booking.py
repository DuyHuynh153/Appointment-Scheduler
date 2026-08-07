"""BookingService - the core booking use case (see ADR-002, ADR-005).

Owns the entire booking flow and its transaction boundary: validate
dealer/vehicle/service type -> assign technician + bay -> re-check
availability under row locks -> overlap check -> insert, all inside a
single DB transaction. This is the only place the no-overlap invariant
is enforced (IMPLEMENTATION_PLAN.md Section 9, Section 11).

Framework-agnostic: depends only on a `Session` (constructor-injected)
and repositories, not on FastAPI. Unit-testable with a fake/mocked
`Session` and repositories.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.appointment import Appointment, AppointmentStatus
from app.models.dealer import Dealer
from app.models.service_bay import ServiceBay
from app.models.service_type import ServiceType
from app.models.technician import Technician
from app.models.vehicle import Vehicle
from app.repositories.appointment import AppointmentRepository
from app.repositories.dealer import DealerRepository
from app.repositories.service_bay import ServiceBayRepository
from app.repositories.service_type import ServiceTypeRepository
from app.repositories.technician import TechnicianRepository
from app.repositories.vehicle import VehicleRepository
from app.utils.time import parse_hhmm


class BookingService:
    """Validates and creates appointments with backend-driven technician
    and service bay assignment."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

        self.dealers = DealerRepository(db)
        self.vehicles = VehicleRepository(db)
        self.service_types = ServiceTypeRepository(db)
        self.technicians = TechnicianRepository(db)
        self.bays = ServiceBayRepository(db)
        self.appointments = AppointmentRepository(db)

    def create_appointment(
        self,
        *,
        dealer_id: uuid.UUID,
        vehicle_id: uuid.UUID,
        service_type_id: uuid.UUID,
        start_time: datetime,
        technician_id: uuid.UUID | None = None,
        bay_id: uuid.UUID | None = None,
    ) -> Appointment:
        """Create an appointment, atomically.

        `technician_id`/`bay_id` are only honored when
        `ENABLE_AUTO_ASSIGN` is disabled (see ADR-004 toggle flow) -
        the API layer's Must-Have contract never accepts them from a
        client when auto-assign is on (IMPLEMENTATION_PLAN.md
        Section 10).
        """
        dealer = self._validate_dealer(dealer_id)
        vehicle = self._validate_vehicle(vehicle_id, dealer)
        service_type = self._validate_service_type(service_type_id)

        end_time = start_time + timedelta(minutes=service_type.duration_minutes)
        self._validate_business_hours(start_time, end_time)

        try:
            self._lock_vehicle_and_check_overlap(vehicle_id, start_time, end_time)

            if self.settings.enable_auto_assign:
                technician, bay = self._auto_assign(dealer_id, start_time, end_time)
            else:
                technician, bay = self._assign_explicit(
                    dealer, technician_id, bay_id, start_time, end_time
                )

            appointment = Appointment(
                dealer_id=dealer_id,
                vehicle_id=vehicle_id,
                service_type_id=service_type_id,
                technician_id=technician.id,
                bay_id=bay.id,
                start_time=start_time,
                end_time=end_time,
            )
            self.appointments.add(appointment)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(appointment)
        return appointment

    # --- Reads / cancellation ------------------------------------------

    def get_appointment(self, appointment_id: uuid.UUID) -> Appointment:
        appointment = self.appointments.get_by_id(appointment_id)
        if appointment is None:
            raise NotFoundError(f"Appointment {appointment_id} not found.")
        return appointment

    def list_appointments(
        self,
        dealer_id: uuid.UUID,
        *,
        appointment_date: date | None = None,
        technician_id: uuid.UUID | None = None,
        status: AppointmentStatus | None = None,
    ) -> list[Appointment]:
        self._validate_dealer(dealer_id)
        return self.appointments.list_by_dealer(
            dealer_id,
            appointment_date=appointment_date,
            technician_id=technician_id,
            status=status,
        )

    def cancel_appointment(self, appointment_id: uuid.UUID) -> Appointment:
        """Soft-cancels an appointment (status -> CANCELLED), per ADR-006.
        Rejects an already-cancelled appointment with `ConflictError` so
        the API layer can map it to `409` (Section 10)."""
        appointment = self.get_appointment(appointment_id)
        if appointment.status == AppointmentStatus.CANCELLED:
            raise ConflictError(f"Appointment {appointment_id} is already cancelled.")

        try:
            appointment.status = AppointmentStatus.CANCELLED
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(appointment)
        return appointment

    # --- Validation ---------------------------------------------------

    def _validate_dealer(self, dealer_id: uuid.UUID) -> Dealer:
        dealer = self.dealers.get_by_id(dealer_id)
        if dealer is None:
            raise NotFoundError(f"Dealer {dealer_id} not found.")
        return dealer

    def _validate_vehicle(self, vehicle_id: uuid.UUID, dealer: Dealer) -> Vehicle:
        vehicle = self.vehicles.get_by_id(vehicle_id)
        if vehicle is None:
            raise NotFoundError(f"Vehicle {vehicle_id} not found.")
        if vehicle.dealer_id != dealer.id:
            raise ValidationError(
                f"Vehicle {vehicle_id} does not belong to dealer {dealer.id}."
            )
        return vehicle

    def _validate_service_type(self, service_type_id: uuid.UUID) -> ServiceType:
        service_type = self.service_types.get_by_id(service_type_id)
        if service_type is None:
            raise NotFoundError(f"Service type {service_type_id} not found.")
        return service_type

    def _validate_business_hours(self, start_time: datetime, end_time: datetime) -> None:
        """Enforces the fixed, system-wide business-hours window (see
        IMPLEMENTATION_PLAN.md Section 4/9): the whole appointment must
        fall within `[business_hours_start, business_hours_end]` on the
        same calendar day."""
        hours_start = parse_hhmm(self.settings.business_hours_start)
        hours_end = parse_hhmm(self.settings.business_hours_end)

        if start_time.date() != end_time.date():
            raise ValidationError("Appointment must not span multiple calendar days.")
        if not (hours_start <= start_time.time() and end_time.time() <= hours_end):
            raise ValidationError(
                f"Appointment must fall within business hours "
                f"({self.settings.business_hours_start}-{self.settings.business_hours_end})."
            )

    # --- Resource assignment -------------------------------------------

    def _lock_vehicle_and_check_overlap(
        self, vehicle_id: uuid.UUID, start_time: datetime, end_time: datetime
    ) -> None:
        """Re-checks the vehicle under a row lock (ADR-005 amendment)
        before the overlap check, closing the check-then-act race
        window for the vehicle's own no-double-booking invariant."""
        self.vehicles.lock_for_update(vehicle_id)
        if self.settings.enable_overlap_validation and self.appointments.has_vehicle_overlap(
            vehicle_id, start_time, end_time
        ):
            raise ConflictError(
                f"Vehicle {vehicle_id} already has an appointment overlapping this time window."
            )

    def _auto_assign(
        self, dealer_id: uuid.UUID, start_time: datetime, end_time: datetime
    ) -> tuple[Technician, ServiceBay]:
        """Picks the first available technician and bay for the dealer,
        re-checking each candidate under a row lock immediately before
        the overlap check (ADR-005)."""
        technician = self._find_available_technician(dealer_id, start_time, end_time)
        if technician is None:
            raise ConflictError("No technician available for the requested time window.")

        bay = self._find_available_bay(dealer_id, start_time, end_time)
        if bay is None:
            raise ConflictError("No service bay available for the requested time window.")

        return technician, bay

    def _find_available_technician(
        self, dealer_id: uuid.UUID, start_time: datetime, end_time: datetime
    ) -> Technician | None:
        for candidate in self.technicians.list_by_dealer(dealer_id):
            locked = self.technicians.lock_for_update(candidate.id)
            if locked is None:
                continue
            if not self.settings.enable_overlap_validation or not self.appointments.has_technician_overlap(
                locked.id, start_time, end_time
            ):
                return locked
        return None

    def _find_available_bay(
        self, dealer_id: uuid.UUID, start_time: datetime, end_time: datetime
    ) -> ServiceBay | None:
        for candidate in self.bays.list_by_dealer(dealer_id):
            locked = self.bays.lock_for_update(candidate.id)
            if locked is None:
                continue
            if not self.settings.enable_overlap_validation or not self.appointments.has_bay_overlap(
                locked.id, start_time, end_time
            ):
                return locked
        return None

    def _assign_explicit(
        self,
        dealer: Dealer,
        technician_id: uuid.UUID | None,
        bay_id: uuid.UUID | None,
        start_time: datetime,
        end_time: datetime,
    ) -> tuple[Technician, ServiceBay]:
        """Manual-assignment path used only when `ENABLE_AUTO_ASSIGN` is
        disabled (ADR-004 toggle flow)."""
        if technician_id is None or bay_id is None:
            raise ValidationError(
                "technician_id and bay_id are required when auto-assign is disabled."
            )

        technician = self.technicians.lock_for_update(technician_id)
        if technician is None or technician.dealer_id != dealer.id:
            raise NotFoundError(f"Technician {technician_id} not found for dealer {dealer.id}.")
        if self.settings.enable_overlap_validation and self.appointments.has_technician_overlap(
            technician.id, start_time, end_time
        ):
            raise ConflictError(f"Technician {technician_id} is not available for this time window.")

        bay = self.bays.lock_for_update(bay_id)
        if bay is None or bay.dealer_id != dealer.id:
            raise NotFoundError(f"Service bay {bay_id} not found for dealer {dealer.id}.")
        if self.settings.enable_overlap_validation and self.appointments.has_bay_overlap(
            bay.id, start_time, end_time
        ):
            raise ConflictError(f"Service bay {bay_id} is not available for this time window.")

        return technician, bay

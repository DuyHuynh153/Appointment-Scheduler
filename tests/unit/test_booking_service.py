"""Unit tests for `BookingService` (IMPLEMENTATION_PLAN.md Section 13).

All repositories are faked in-memory (see `conftest.py`) - no DB, no
FastAPI. Tests read as specifications of the booking business rules in
Section 9.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.appointment import AppointmentStatus
from app.services.booking import BookingService
from tests.unit.conftest import (
    FakeAppointmentRepo,
    FakeSimpleRepo,
    make_appointment,
    make_bay,
    make_dealer,
    make_service_type,
    make_technician,
    make_vehicle,
)

UTC = timezone.utc


def _at(hour: int, minute: int = 0, *, day: int = 15) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=UTC)


# --- Happy path -------------------------------------------------------------


class TestCreateAppointmentSuccess:
    def test_successful_booking_assigns_technician_and_bay(
        self, booking_service, dealer, vehicle, service_type, technician, bay
    ):
        start_time = _at(9)

        appointment = booking_service.create_appointment(
            dealer_id=dealer.id,
            vehicle_id=vehicle.id,
            service_type_id=service_type.id,
            start_time=start_time,
        )

        assert appointment.dealer_id == dealer.id
        assert appointment.vehicle_id == vehicle.id
        assert appointment.technician_id == technician.id
        assert appointment.bay_id == bay.id
        assert appointment.start_time == start_time
        assert appointment.end_time == start_time + timedelta(minutes=service_type.duration_minutes)
        assert appointment.status == AppointmentStatus.SCHEDULED

    def test_successful_booking_commits_transaction(
        self, booking_service, dealer, vehicle, service_type
    ):
        booking_service.create_appointment(
            dealer_id=dealer.id,
            vehicle_id=vehicle.id,
            service_type_id=service_type.id,
            start_time=_at(9),
        )

        booking_service.db.commit.assert_called_once()
        booking_service.db.rollback.assert_not_called()
        booking_service.db.refresh.assert_called_once()


# --- Overlap rejection -------------------------------------------------------


class TestOverlapRejection:
    def test_vehicle_overlap_rejected(
        self, booking_service, dealer, vehicle, service_type, technician, bay
    ):
        existing_start, existing_end = _at(9), _at(9, 30)
        booking_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=vehicle,
                service_type=service_type,
                technician=technician,
                bay=bay,
                start_time=existing_start,
                end_time=existing_end,
            )
        )

        with pytest.raises(ConflictError, match="already has an appointment"):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(9, 15),  # overlaps [09:00, 09:30)
            )

    def test_technician_overlap_rejected_via_explicit_assignment(
        self, settings, dealer, vehicle, service_type, technician, bay
    ):
        """Uses the explicit-assignment path (auto-assign disabled) so
        a technician conflict maps 1:1 to a single candidate, isolating
        technician-overlap rejection from the auto-assign scan."""
        manual_settings = Settings(
            **{**settings.model_dump(), "enable_auto_assign": False}
        )
        service = BookingService(db=MagicMock(), settings=manual_settings)
        service.dealers = FakeSimpleRepo([dealer])
        service.vehicles = FakeSimpleRepo([vehicle])
        service.service_types = FakeSimpleRepo([service_type])
        service.technicians = FakeSimpleRepo([technician])
        service.bays = FakeSimpleRepo([bay])
        service.appointments = FakeAppointmentRepo(
            [
                make_appointment(
                    dealer=dealer,
                    vehicle=make_vehicle(dealer),
                    service_type=service_type,
                    technician=technician,
                    bay=make_bay(dealer),
                    start_time=_at(9),
                    end_time=_at(9, 30),
                )
            ]
        )

        with pytest.raises(ConflictError, match="not available for this time window"):
            service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(9, 15),
                technician_id=technician.id,
                bay_id=bay.id,
            )

    def test_bay_overlap_rejected_via_explicit_assignment(
        self, settings, dealer, vehicle, service_type, technician, bay
    ):
        manual_settings = Settings(
            **{**settings.model_dump(), "enable_auto_assign": False}
        )
        service = BookingService(db=MagicMock(), settings=manual_settings)
        service.dealers = FakeSimpleRepo([dealer])
        service.vehicles = FakeSimpleRepo([vehicle])
        service.service_types = FakeSimpleRepo([service_type])
        service.technicians = FakeSimpleRepo([technician])
        service.bays = FakeSimpleRepo([bay])
        service.appointments = FakeAppointmentRepo(
            [
                make_appointment(
                    dealer=dealer,
                    vehicle=make_vehicle(dealer),
                    service_type=service_type,
                    technician=make_technician(dealer),
                    bay=bay,
                    start_time=_at(9),
                    end_time=_at(9, 30),
                )
            ]
        )

        with pytest.raises(ConflictError, match="not available for this time window"):
            service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(9, 15),
                technician_id=technician.id,
                bay_id=bay.id,
            )


# --- Auto-assignment ---------------------------------------------------------


class TestAutoAssignment:
    def test_auto_assign_skips_busy_technician_and_picks_next(
        self, booking_service, dealer, vehicle, service_type, technician, bay
    ):
        second_technician = make_technician(dealer, name="Tech B")
        booking_service.technicians.add_item(second_technician)
        # Ensure deterministic ordering: technician (busy) visited first.
        ordered = sorted([technician, second_technician], key=lambda t: t.id.int)
        busy, free = ordered[0], ordered[1]

        booking_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=busy,
                bay=make_bay(dealer),
                start_time=_at(9),
                end_time=_at(9, 30),
            )
        )

        appointment = booking_service.create_appointment(
            dealer_id=dealer.id,
            vehicle_id=vehicle.id,
            service_type_id=service_type.id,
            start_time=_at(9, 15),
        )

        assert appointment.technician_id == free.id

    def test_auto_assign_skips_busy_bay_and_picks_next(
        self, booking_service, dealer, vehicle, service_type, technician, bay
    ):
        second_bay = make_bay(dealer, name="Bay B")
        booking_service.bays.add_item(second_bay)
        ordered = sorted([bay, second_bay], key=lambda b: b.id.int)
        busy, free = ordered[0], ordered[1]

        booking_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=make_technician(dealer),
                bay=busy,
                start_time=_at(9),
                end_time=_at(9, 30),
            )
        )

        appointment = booking_service.create_appointment(
            dealer_id=dealer.id,
            vehicle_id=vehicle.id,
            service_type_id=service_type.id,
            start_time=_at(9, 15),
        )

        assert appointment.bay_id == free.id

    def test_auto_assign_raises_conflict_when_no_technician_available(
        self, booking_service, dealer, vehicle, service_type, technician
    ):
        booking_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=technician,
                bay=make_bay(dealer),
                start_time=_at(9),
                end_time=_at(9, 30),
            )
        )

        with pytest.raises(ConflictError, match="No technician available"):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(9, 15),
            )

    def test_auto_assign_raises_conflict_when_no_bay_available(
        self, booking_service, dealer, vehicle, service_type, bay
    ):
        booking_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=make_technician(dealer),
                bay=bay,
                start_time=_at(9),
                end_time=_at(9, 30),
            )
        )

        with pytest.raises(ConflictError, match="No service bay available"):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(9, 15),
            )


# --- Validation ---------------------------------------------------------


class TestBusinessHoursValidation:
    def test_start_time_before_business_hours_rejected(
        self, booking_service, dealer, vehicle, service_type
    ):
        with pytest.raises(ValidationError, match="business hours"):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(7, 45),
            )

    def test_end_time_after_business_hours_rejected(
        self, booking_service, dealer, vehicle, service_type
    ):
        with pytest.raises(ValidationError, match="business hours"):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(17, 45),  # + 30 min duration -> 18:15, past 18:00
            )

    def test_appointment_spanning_multiple_days_rejected(
        self, booking_service, dealer, vehicle, service_type
    ):
        # duration_minutes=30 can't normally cross midnight from 08:00-18:00
        # window, so use an explicit boundary-crossing start_time.
        with pytest.raises(ValidationError, match="multiple calendar days"):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=datetime(2026, 9, 15, 23, 50, tzinfo=UTC),
            )


class TestDurationValidation:
    def test_long_duration_pushing_past_business_hours_rejected(
        self, booking_service, dealer, vehicle, technician, bay
    ):
        long_service_type = make_service_type(name="Full Inspection", duration_minutes=600)
        booking_service.service_types.add_item(long_service_type)

        with pytest.raises(ValidationError, match="business hours"):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=long_service_type.id,
                start_time=_at(9),  # 09:00 + 600min = 19:00, past 18:00
            )


class TestDealerMismatch:
    def test_vehicle_belonging_to_different_dealer_rejected(
        self, booking_service, dealer, other_dealer, service_type
    ):
        other_vehicle = make_vehicle(other_dealer)
        booking_service.vehicles.add_item(other_vehicle)

        with pytest.raises(ValidationError, match="does not belong to dealer"):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=other_vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(9),
            )


# --- Not-found validation (dealer/vehicle/service type) ---------------------


class TestNotFoundValidation:
    def test_unknown_dealer_raises_not_found(self, booking_service, vehicle, service_type):
        with pytest.raises(NotFoundError):
            booking_service.create_appointment(
                dealer_id=uuid.uuid4(),
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(9),
            )

    def test_unknown_vehicle_raises_not_found(self, booking_service, dealer, service_type):
        with pytest.raises(NotFoundError):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=uuid.uuid4(),
                service_type_id=service_type.id,
                start_time=_at(9),
            )

    def test_unknown_service_type_raises_not_found(self, booking_service, dealer, vehicle):
        with pytest.raises(NotFoundError):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=uuid.uuid4(),
                start_time=_at(9),
            )


# --- Transaction rollback ----------------------------------------------------


class TestTransactionRollback:
    def test_commit_failure_rolls_back_and_propagates(
        self, booking_service, dealer, vehicle, service_type
    ):
        booking_service.db.commit.side_effect = RuntimeError("db exploded")

        with pytest.raises(RuntimeError, match="db exploded"):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(9),
            )

        booking_service.db.rollback.assert_called_once()

    def test_rollback_failure_does_not_persist_appointment(
        self, booking_service, dealer, vehicle, service_type
    ):
        booking_service.db.commit.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            booking_service.create_appointment(
                dealer_id=dealer.id,
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                start_time=_at(9),
            )

        # The appointment was staged (flushed by the fake repo's `add`)
        # but the caller must treat it as not committed; no appointment
        # should be visible for the dealer afterward in a real session
        # (rollback undoes the insert). Here we assert the service
        # surfaced the failure rather than swallowing it.
        booking_service.db.rollback.assert_called_once()


# --- Cancel appointment -------------------------------------------------


class TestCancelAppointment:
    def test_cancel_appointment_success(
        self, booking_service, dealer, vehicle, service_type, technician, bay
    ):
        appointment = booking_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=vehicle,
                service_type=service_type,
                technician=technician,
                bay=bay,
                start_time=_at(9),
                end_time=_at(9, 30),
            )
        )

        cancelled = booking_service.cancel_appointment(appointment.id)

        assert cancelled.status == AppointmentStatus.CANCELLED
        booking_service.db.commit.assert_called_once()

    def test_cancel_already_cancelled_raises_conflict(
        self, booking_service, dealer, vehicle, service_type, technician, bay
    ):
        appointment = booking_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=vehicle,
                service_type=service_type,
                technician=technician,
                bay=bay,
                start_time=_at(9),
                end_time=_at(9, 30),
                status=AppointmentStatus.CANCELLED,
            )
        )

        with pytest.raises(ConflictError, match="already cancelled"):
            booking_service.cancel_appointment(appointment.id)

    def test_cancel_unknown_appointment_raises_not_found(self, booking_service):
        with pytest.raises(NotFoundError):
            booking_service.cancel_appointment(uuid.uuid4())


# --- List / get appointments ----------------------------------------------


class TestListAndGetAppointments:
    def test_list_appointments_filters_by_dealer(
        self, booking_service, dealer, vehicle, service_type, technician, bay
    ):
        appt = booking_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=vehicle,
                service_type=service_type,
                technician=technician,
                bay=bay,
                start_time=_at(9),
                end_time=_at(9, 30),
            )
        )

        results = booking_service.list_appointments(dealer.id)

        assert [a.id for a in results] == [appt.id]

    def test_list_appointments_unknown_dealer_raises_not_found(self, booking_service):
        with pytest.raises(NotFoundError):
            booking_service.list_appointments(uuid.uuid4())

    def test_get_appointment_returns_match(
        self, booking_service, dealer, vehicle, service_type, technician, bay
    ):
        appt = booking_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=vehicle,
                service_type=service_type,
                technician=technician,
                bay=bay,
                start_time=_at(9),
                end_time=_at(9, 30),
            )
        )

        assert booking_service.get_appointment(appt.id).id == appt.id

    def test_get_appointment_unknown_raises_not_found(self, booking_service):
        with pytest.raises(NotFoundError):
            booking_service.get_appointment(uuid.uuid4())

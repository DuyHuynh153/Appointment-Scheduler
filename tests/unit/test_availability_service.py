"""Unit tests for `AvailabilityService` (IMPLEMENTATION_PLAN.md
Section 13). Reuses the fakes/factories from Group 1's
`tests/unit/conftest.py` - no DB, no FastAPI.

`AvailabilityService` is a pure read: it must never lock rows, add
appointments, or commit/rollback a transaction (see
`app/services/availability.py` module docstring).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import NotFoundError
from tests.unit.conftest import (
    FakeAppointmentRepo,
    FakeSimpleRepo,
    make_appointment,
    make_bay,
    make_technician,
    make_vehicle,
)

UTC = timezone.utc
TARGET_DATE = date(2026, 9, 15)


def _slot_dt(hour: int, minute: int = 0):
    from datetime import datetime

    return datetime(2026, 9, 15, hour, minute, tzinfo=UTC)


# --- Empty / fully / partially occupied schedules --------------------------


class TestScheduleOccupancy:
    def test_empty_schedule_no_resources_returns_zero_availability_every_slot(
        self, availability_service, dealer, service_type
    ):
        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )

        assert len(slots) > 0
        assert all(s.available_technicians == 0 for s in slots)
        assert all(s.available_bays == 0 for s in slots)

    def test_partially_occupied_schedule_only_affects_overlapping_slot(
        self, availability_service, dealer, service_type
    ):
        technician = make_technician(dealer)
        bay = make_bay(dealer)
        availability_service.technicians.add_item(technician)
        availability_service.bays.add_item(bay)

        availability_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=technician,
                bay=bay,
                start_time=_slot_dt(9),
                end_time=_slot_dt(9, 30),
            )
        )

        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )

        busy_slot = next(s for s in slots if s.start_time == _slot_dt(9))
        free_slot = next(s for s in slots if s.start_time == _slot_dt(10))

        assert busy_slot.available_technicians == 0
        assert busy_slot.available_bays == 0
        assert free_slot.available_technicians == 1
        assert free_slot.available_bays == 1

    def test_fully_occupied_schedule_zero_availability_all_slots(
        self, availability_service, dealer, service_type
    ):
        technician = make_technician(dealer)
        bay = make_bay(dealer)
        availability_service.technicians.add_item(technician)
        availability_service.bays.add_item(bay)

        # One appointment spanning the entire business-hours window.
        availability_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=technician,
                bay=bay,
                start_time=_slot_dt(8),
                end_time=_slot_dt(18),
            )
        )

        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )

        assert len(slots) > 0
        assert all(s.available_technicians == 0 for s in slots)
        assert all(s.available_bays == 0 for s in slots)


# --- Technician / bay busy in isolation -------------------------------------


class TestResourceIndependence:
    def test_technician_busy_bay_free_counts_independently(
        self, availability_service, dealer, service_type
    ):
        technician = make_technician(dealer)
        bay = make_bay(dealer)
        availability_service.technicians.add_item(technician)
        availability_service.bays.add_item(bay)

        # Technician has an appointment (at some other bay) blocking 09:00.
        other_bay = make_bay(dealer)
        availability_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=technician,
                bay=other_bay,
                start_time=_slot_dt(9),
                end_time=_slot_dt(9, 30),
            )
        )

        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )
        busy_slot = next(s for s in slots if s.start_time == _slot_dt(9))

        assert busy_slot.available_technicians == 0
        assert busy_slot.available_bays == 1  # `bay` itself is untouched

    def test_bay_busy_technician_free_counts_independently(
        self, availability_service, dealer, service_type
    ):
        technician = make_technician(dealer)
        bay = make_bay(dealer)
        availability_service.technicians.add_item(technician)
        availability_service.bays.add_item(bay)

        other_technician = make_technician(dealer)
        availability_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=other_technician,
                bay=bay,
                start_time=_slot_dt(9),
                end_time=_slot_dt(9, 30),
            )
        )

        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )
        busy_slot = next(s for s in slots if s.start_time == _slot_dt(9))

        assert busy_slot.available_bays == 0
        assert busy_slot.available_technicians == 1  # `technician` itself is free


# --- Multiple technicians / bays --------------------------------------------


class TestMultipleResources:
    def test_multiple_technicians_partial_busy_counts_correctly(
        self, availability_service, dealer, service_type
    ):
        busy = make_technician(dealer, name="Busy Tech")
        free_a = make_technician(dealer, name="Free Tech A")
        free_b = make_technician(dealer, name="Free Tech B")
        for tech in (busy, free_a, free_b):
            availability_service.technicians.add_item(tech)

        availability_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=busy,
                bay=make_bay(dealer),
                start_time=_slot_dt(9),
                end_time=_slot_dt(9, 30),
            )
        )

        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )
        busy_slot = next(s for s in slots if s.start_time == _slot_dt(9))
        free_slot = next(s for s in slots if s.start_time == _slot_dt(10))

        assert busy_slot.available_technicians == 2
        assert free_slot.available_technicians == 3

    def test_multiple_bays_partial_busy_counts_correctly(
        self, availability_service, dealer, service_type
    ):
        busy = make_bay(dealer, name="Busy Bay")
        free_a = make_bay(dealer, name="Free Bay A")
        free_b = make_bay(dealer, name="Free Bay B")
        for b in (busy, free_a, free_b):
            availability_service.bays.add_item(b)

        availability_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=make_technician(dealer),
                bay=busy,
                start_time=_slot_dt(9),
                end_time=_slot_dt(9, 30),
            )
        )

        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )
        busy_slot = next(s for s in slots if s.start_time == _slot_dt(9))
        free_slot = next(s for s in slots if s.start_time == _slot_dt(10))

        assert busy_slot.available_bays == 2
        assert free_slot.available_bays == 3


# --- Slot generation: count / contiguity / business hours / duration -------


class TestSlotGeneration:
    def test_multiple_slots_returned_for_full_business_day(
        self, availability_service, dealer, service_type
    ):
        # 08:00-18:00 window, 30-min service -> 20 contiguous slots.
        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )

        assert len(slots) == 20

    def test_business_hours_respected(self, availability_service, dealer, service_type):
        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )

        assert slots[0].start_time == _slot_dt(8)
        assert slots[-1].end_time == _slot_dt(18)
        assert all(s.start_time.time() >= _slot_dt(8).time() for s in slots)
        assert all(s.end_time.time() <= _slot_dt(18).time() for s in slots)

    def test_slot_duration_matches_service_type_and_slots_are_contiguous(
        self, availability_service, dealer, service_type
    ):
        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )

        duration = timedelta(minutes=service_type.duration_minutes)
        assert all(s.end_time - s.start_time == duration for s in slots)
        for earlier, later in zip(slots, slots[1:]):
            assert earlier.end_time == later.start_time  # no gaps, no overlap

    def test_no_available_slot_when_duration_exceeds_business_hours(
        self, availability_service, dealer
    ):
        from tests.unit.conftest import make_service_type

        long_service_type = make_service_type(duration_minutes=700)  # > 10h window
        availability_service.service_types.add_item(long_service_type)

        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=long_service_type.id, target_date=TARGET_DATE
        )

        assert slots == []


# --- Not-found validation ----------------------------------------------------


class TestNotFoundValidation:
    def test_dealer_not_found_raises(self, availability_service, service_type):
        with pytest.raises(NotFoundError):
            availability_service.get_availability(
                dealer_id=uuid.uuid4(),
                service_type_id=service_type.id,
                target_date=TARGET_DATE,
            )

    def test_service_type_not_found_raises(self, availability_service, dealer):
        with pytest.raises(NotFoundError):
            availability_service.get_availability(
                dealer_id=dealer.id,
                service_type_id=uuid.uuid4(),
                target_date=TARGET_DATE,
            )


# --- UTC handling -------------------------------------------------------


class TestUtcHandling:
    def test_slots_are_utc_aware(self, availability_service, dealer, service_type):
        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )

        assert all(s.start_time.tzinfo == UTC for s in slots)
        assert all(s.end_time.tzinfo == UTC for s in slots)

    def test_overlap_check_still_correct_when_appointment_stored_with_non_utc_offset(
        self, availability_service, dealer, service_type
    ):
        """Mirrors the Phase 4 UTC-normalization fix: any offset-aware
        datetime is equivalent once normalized, so an appointment whose
        `start_time`/`end_time` carry a non-UTC (but still aware)
        offset must still be detected as overlapping a UTC-based slot.
        """
        from datetime import timezone as tz

        plus_two = tz(timedelta(hours=2))
        technician = make_technician(dealer)
        bay = make_bay(dealer)
        availability_service.technicians.add_item(technician)
        availability_service.bays.add_item(bay)

        # 11:00+02:00 == 09:00 UTC
        availability_service.appointments.add(
            make_appointment(
                dealer=dealer,
                vehicle=make_vehicle(dealer),
                service_type=service_type,
                technician=technician,
                bay=bay,
                start_time=_slot_dt(9).astimezone(plus_two),
                end_time=_slot_dt(9, 30).astimezone(plus_two),
            )
        )

        slots = availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )
        busy_slot = next(s for s in slots if s.start_time == _slot_dt(9))

        assert busy_slot.available_technicians == 0
        assert busy_slot.available_bays == 0


# --- Read-only guarantees ----------------------------------------------------


class TestReadOnlyGuarantees:
    def test_no_transaction_is_committed_or_rolled_back(
        self, availability_service, dealer, service_type
    ):
        availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )

        availability_service.db.commit.assert_not_called()
        availability_service.db.rollback.assert_not_called()
        availability_service.db.add.assert_not_called()

    def test_no_rows_are_locked_and_no_appointments_are_added(
        self, availability_service, dealer, service_type
    ):
        technician = make_technician(dealer)
        bay = make_bay(dealer)

        # Spy on the fakes: `lock_for_update`/`add` must never be
        # called by a purely read-only availability query.
        tech_repo = MagicMock(wraps=FakeSimpleRepo([technician]))
        bay_repo = MagicMock(wraps=FakeSimpleRepo([bay]))
        appt_repo = MagicMock(wraps=FakeAppointmentRepo())

        availability_service.technicians = tech_repo
        availability_service.bays = bay_repo
        availability_service.appointments = appt_repo

        availability_service.get_availability(
            dealer_id=dealer.id, service_type_id=service_type.id, target_date=TARGET_DATE
        )

        tech_repo.lock_for_update.assert_not_called()
        bay_repo.lock_for_update.assert_not_called()
        appt_repo.add.assert_not_called()

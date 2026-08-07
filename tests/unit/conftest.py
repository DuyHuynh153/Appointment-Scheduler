"""Shared fixtures/fakes for service-layer unit tests (no DB - see
IMPLEMENTATION_PLAN.md Section 13: "Unit tests (service layer,
repositories mocked/faked, no DB)").

`BookingService`/`AvailabilityService` build their own repository
instances in `__init__`, so these fakes are swapped in *after*
construction by pointing the service's `self.<repo_attr>` at a fake
that implements the same narrow surface area the services actually
call. This keeps the services' production code completely untouched
while giving tests full control over persisted state without a real
Postgres connection.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.dealer import Dealer
from app.models.service_bay import ServiceBay
from app.models.service_type import ServiceType
from app.models.technician import Technician
from app.models.vehicle import Vehicle
from app.services.availability import AvailabilityService
from app.services.booking import BookingService

UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(UTC)


# --- Model factories (plain in-memory instances, no DB) ------------------


def make_dealer(**overrides) -> Dealer:
    defaults = dict(id=uuid.uuid4(), name="Test Dealer", timezone="UTC")
    defaults.update(overrides)
    return Dealer(**defaults)


def make_vehicle(dealer: Dealer, **overrides) -> Vehicle:
    defaults = dict(
        id=uuid.uuid4(), dealer_id=dealer.id, vin="1HGCM82633A004352", owner_name="Jane Doe"
    )
    defaults.update(overrides)
    return Vehicle(**defaults)


def make_technician(dealer: Dealer, **overrides) -> Technician:
    defaults = dict(id=uuid.uuid4(), dealer_id=dealer.id, name="Tech")
    defaults.update(overrides)
    return Technician(**defaults)


def make_bay(dealer: Dealer, **overrides) -> ServiceBay:
    defaults = dict(id=uuid.uuid4(), dealer_id=dealer.id, name="Bay")
    defaults.update(overrides)
    return ServiceBay(**defaults)


def make_service_type(**overrides) -> ServiceType:
    defaults = dict(id=uuid.uuid4(), name="Oil Change", duration_minutes=30)
    defaults.update(overrides)
    return ServiceType(**defaults)


def make_appointment(
    *,
    dealer: Dealer,
    vehicle: Vehicle,
    service_type: ServiceType,
    technician: Technician,
    bay: ServiceBay,
    start_time: datetime,
    end_time: datetime,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
    **overrides,
) -> Appointment:
    defaults = dict(
        id=uuid.uuid4(),
        dealer_id=dealer.id,
        vehicle_id=vehicle.id,
        service_type_id=service_type.id,
        technician_id=technician.id,
        bay_id=bay.id,
        start_time=start_time,
        end_time=end_time,
        status=status,
        created_at=_now(),
        updated_at=_now(),
    )
    defaults.update(overrides)
    return Appointment(**defaults)


# --- Fake repositories -----------------------------------------------------


class FakeSimpleRepo:
    """Fakes `BaseRepository` subclasses that only ever need
    `get_by_id`/`list_by_dealer`/`lock_for_update` (Dealer, Vehicle,
    ServiceType, Technician, ServiceBay repos)."""

    def __init__(self, items: list | None = None) -> None:
        self._store: dict[uuid.UUID, object] = {item.id: item for item in (items or [])}

    def add_item(self, item) -> None:
        self._store[item.id] = item

    def get_by_id(self, id: uuid.UUID):
        return self._store.get(id)

    def list_by_dealer(self, dealer_id: uuid.UUID) -> list:
        return sorted(
            (item for item in self._store.values() if item.dealer_id == dealer_id),
            key=lambda item: item.id.int if isinstance(item.id, uuid.UUID) else 0,
        )

    def lock_for_update(self, id: uuid.UUID):
        """Mirrors the real repo: `SELECT ... FOR UPDATE` returns
        `None` if the row no longer exists, otherwise the row."""
        return self._store.get(id)


class FakeAppointmentRepo:
    """Fakes `AppointmentRepository`: reproduces the exact half-open
    `[start, end)` overlap semantics of the real `_has_overlap` SQL so
    unit tests exercise realistic overlap decisions, not a stub that
    always returns a canned bool."""

    _ACTIVE_STATUSES = (AppointmentStatus.SCHEDULED,)

    def __init__(self, items: list[Appointment] | None = None) -> None:
        self._items: list[Appointment] = list(items or [])

    def add(self, appointment: Appointment) -> Appointment:
        """Mimics the persistence-layer defaults a real `db.flush()`
        would populate (id/status/timestamps) - `BookingService`
        constructs a plain `Appointment(...)` without setting `status`,
        relying on the SQLAlchemy column default, which only applies
        on an actual flush/insert, not on bare instantiation."""
        if appointment.id is None:
            appointment.id = uuid.uuid4()
        if appointment.status is None:
            appointment.status = AppointmentStatus.SCHEDULED
        if appointment.created_at is None:
            appointment.created_at = _now()
        if appointment.updated_at is None:
            appointment.updated_at = _now()
        self._items.append(appointment)
        return appointment

    def get_by_id(self, id: uuid.UUID) -> Appointment | None:
        return next((a for a in self._items if a.id == id), None)

    def list_by_dealer(
        self,
        dealer_id: uuid.UUID,
        *,
        appointment_date=None,
        technician_id: uuid.UUID | None = None,
        status: AppointmentStatus | None = None,
    ) -> list[Appointment]:
        results = [a for a in self._items if a.dealer_id == dealer_id]
        if appointment_date is not None:
            results = [a for a in results if a.start_time.date() == appointment_date]
        if technician_id is not None:
            results = [a for a in results if a.technician_id == technician_id]
        if status is not None:
            results = [a for a in results if a.status == status]
        return results

    def _has_overlap(self, attr: str, resource_id: uuid.UUID, start_time, end_time) -> bool:
        return any(
            getattr(a, attr) == resource_id
            and a.status in self._ACTIVE_STATUSES
            and a.start_time < end_time
            and a.end_time > start_time
            for a in self._items
        )

    def has_technician_overlap(self, technician_id, start_time, end_time, **_) -> bool:
        return self._has_overlap("technician_id", technician_id, start_time, end_time)

    def has_bay_overlap(self, bay_id, start_time, end_time, **_) -> bool:
        return self._has_overlap("bay_id", bay_id, start_time, end_time)

    def has_vehicle_overlap(self, vehicle_id, start_time, end_time, **_) -> bool:
        return self._has_overlap("vehicle_id", vehicle_id, start_time, end_time)


# --- Pytest fixtures --------------------------------------------------------


@pytest.fixture
def settings() -> Settings:
    return Settings(
        enable_auto_assign=True,
        enable_overlap_validation=True,
        business_hours_start="08:00",
        business_hours_end="18:00",
    )


@pytest.fixture
def dealer() -> Dealer:
    return make_dealer()


@pytest.fixture
def other_dealer() -> Dealer:
    return make_dealer(name="Other Dealer")


@pytest.fixture
def vehicle(dealer) -> Vehicle:
    return make_vehicle(dealer)


@pytest.fixture
def service_type() -> ServiceType:
    return make_service_type(duration_minutes=30)


@pytest.fixture
def technician(dealer) -> Technician:
    return make_technician(dealer, name="Tech A")


@pytest.fixture
def bay(dealer) -> ServiceBay:
    return make_bay(dealer, name="Bay A")


@pytest.fixture
def booking_service(settings, dealer, vehicle, service_type, technician, bay) -> BookingService:
    """A `BookingService` wired to fully in-memory fake repositories,
    seeded with one dealer/vehicle/service_type/technician/bay - the
    minimal happy-path fixture set. Individual tests add more
    technicians/bays/appointments via the exposed fake repo attributes.
    """
    service = BookingService(db=MagicMock(), settings=settings)

    service.dealers = FakeSimpleRepo([dealer])
    service.vehicles = FakeSimpleRepo([vehicle])
    service.service_types = FakeSimpleRepo([service_type])
    service.technicians = FakeSimpleRepo([technician])
    service.bays = FakeSimpleRepo([bay])
    service.appointments = FakeAppointmentRepo()

    return service


@pytest.fixture
def availability_service(settings, dealer, service_type) -> AvailabilityService:
    service = AvailabilityService(db=MagicMock(), settings=settings)

    service.dealers = FakeSimpleRepo([dealer])
    service.service_types = FakeSimpleRepo([service_type])
    service.technicians = FakeSimpleRepo([])
    service.bays = FakeSimpleRepo([])
    service.appointments = FakeAppointmentRepo()

    return service

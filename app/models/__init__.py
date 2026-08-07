"""SQLAlchemy ORM models (persistence shape only, no business logic).

Importing this package registers all entity modules on
`app.db.base.Base.metadata`, which Alembic's autogenerate relies on
(see `migrations/env.py`).

Domain model frozen as of the Domain Model Review, 2026-08-07 - see
IMPLEMENTATION_PLAN.md Sections 6/11 and that review's decisions
(VIN globally unique, half-open overlap intervals, explicit FK
indexes, `updated_at` on all entities, `COMPLETED` status reserved
for future use, service types are global reference data, technician
skill matching out of scope, dealer `timezone` retained for future
extensibility only).
"""
from app.models.appointment import Appointment, AppointmentStatus
from app.models.dealer import Dealer
from app.models.service_bay import ServiceBay
from app.models.service_type import ServiceType
from app.models.technician import Technician
from app.models.vehicle import Vehicle

__all__ = [
    "Appointment",
    "AppointmentStatus",
    "Dealer",
    "ServiceBay",
    "ServiceType",
    "Technician",
    "Vehicle",
]

"""Data-access classes, one per aggregate (see ADR-002).

Each repository wraps the SQLAlchemy queries for a single aggregate
and takes a `Session` via constructor injection. Business rules and
transaction orchestration stay out of this layer - see `app/services/`
(Phase 3, not yet implemented).
"""
from app.repositories.appointment import AppointmentRepository
from app.repositories.dealer import DealerRepository
from app.repositories.service_bay import ServiceBayRepository
from app.repositories.service_type import ServiceTypeRepository
from app.repositories.technician import TechnicianRepository
from app.repositories.vehicle import VehicleRepository

__all__ = [
    "AppointmentRepository",
    "DealerRepository",
    "ServiceBayRepository",
    "ServiceTypeRepository",
    "TechnicianRepository",
    "VehicleRepository",
]

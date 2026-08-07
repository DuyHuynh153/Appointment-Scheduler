"""Shared FastAPI dependencies (dependency injection wiring).

Route handlers depend on these via `Depends(...)` rather than
importing settings/engine/session globals directly, so they stay easy
to override in tests, e.g. `app.dependency_overrides[get_db] = ...`.
"""
from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db as _get_db
from app.services.availability import AvailabilityService
from app.services.booking import BookingService

__all__ = [
    "get_settings",
    "get_db",
    "Settings",
    "get_booking_service",
    "get_availability_service",
]


def get_db() -> Generator[Session, None, None]:
    """Re-exported DB session dependency (see `app.db.session.get_db`)."""
    yield from _get_db()


def get_booking_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingService:
    return BookingService(db, settings=settings)


def get_availability_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AvailabilityService:
    return AvailabilityService(db, settings=settings)


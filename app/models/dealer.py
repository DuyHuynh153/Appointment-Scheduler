"""Dealer ORM model.

Scopes vehicles, technicians, and service bays (see
IMPLEMENTATION_PLAN.md Section 6).
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.service_bay import ServiceBay
    from app.models.technician import Technician
    from app.models.vehicle import Vehicle


class Dealer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dealers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Retained for future multi-timezone extensibility (Domain Model
    # Review, 2026-08-07). Appointment timestamps are always stored
    # and compared in UTC regardless of this field - see
    # IMPLEMENTATION_PLAN.md Section 4.
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="UTC", server_default="UTC"
    )

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="dealer")
    technicians: Mapped[list["Technician"]] = relationship(back_populates="dealer")
    service_bays: Mapped[list["ServiceBay"]] = relationship(back_populates="dealer")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="dealer")

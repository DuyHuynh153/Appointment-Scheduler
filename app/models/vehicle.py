"""Vehicle ORM model.

VIN is globally unique across dealers (Domain Model Review,
2026-08-07) - a vehicle belongs to exactly one dealer (see
IMPLEMENTATION_PLAN.md Section 4 assumptions).
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.dealer import Dealer


class Vehicle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vehicles"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vin: Mapped[str] = mapped_column(String(17), nullable=False, unique=True)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)

    dealer: Mapped["Dealer"] = relationship(back_populates="vehicles")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="vehicle")

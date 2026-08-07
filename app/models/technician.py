"""Technician ORM model.

Skill-based matching is explicitly out of scope for this assessment
(Domain Model Review, 2026-08-07) - auto-assignment is availability-only
(no skill tags column).
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


class Technician(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "technicians"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    dealer: Mapped["Dealer"] = relationship(back_populates="technicians")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="technician")

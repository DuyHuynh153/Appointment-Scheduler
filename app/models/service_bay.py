"""Service Bay ORM model - a physical resource scoped to one dealer."""
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


class ServiceBay(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "service_bays"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    dealer: Mapped["Dealer"] = relationship(back_populates="service_bays")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="bay")

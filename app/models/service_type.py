"""Service Type ORM model - global reference data (Domain Model Review,
2026-08-07: not dealer-scoped; the same catalog and durations apply
across all dealers for this assessment)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.appointment import Appointment


class ServiceType(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "service_types"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_service_types_duration_positive"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="service_type")

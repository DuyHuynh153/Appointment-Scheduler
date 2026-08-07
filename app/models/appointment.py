"""Appointment ORM model - the central aggregate enforcing the
no-overlap invariants (see ADR-005 and its amendment).

Overlap semantics use half-open intervals `[start_time, end_time)`
(Domain Model Review, 2026-08-07): two appointments where one's
`end_time` equals another's `start_time` are NOT considered
overlapping. That comparison lives in the service/repository layer
(not yet implemented) - this model only carries the CHECK constraint
that `end_time > start_time`.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.dealer import Dealer
    from app.models.service_bay import ServiceBay
    from app.models.service_type import ServiceType
    from app.models.technician import Technician
    from app.models.vehicle import Vehicle


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    # Reserved for a future completion workflow (Domain Model Review,
    # 2026-08-07): not reachable via any endpoint in this assessment.
    COMPLETED = "COMPLETED"


class Appointment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_appointments_end_after_start"),
        Index("ix_appointments_technician_time", "technician_id", "start_time", "end_time"),
        Index("ix_appointments_bay_time", "bay_id", "start_time", "end_time"),
        Index("ix_appointments_vehicle_time", "vehicle_id", "start_time", "end_time"),
        Index("ix_appointments_dealer_start", "dealer_id", "start_time"),
    )

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("dealers.id", ondelete="RESTRICT"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )
    service_type_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("service_types.id", ondelete="RESTRICT"), nullable=False
    )
    technician_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("technicians.id", ondelete="RESTRICT"), nullable=False
    )
    bay_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("service_bays.id", ondelete="RESTRICT"), nullable=False
    )

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status", native_enum=True),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
        server_default=AppointmentStatus.SCHEDULED.value,
    )

    dealer: Mapped["Dealer"] = relationship(back_populates="appointments")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="appointments")
    service_type: Mapped["ServiceType"] = relationship(back_populates="appointments")
    technician: Mapped["Technician"] = relationship(back_populates="appointments")
    bay: Mapped["ServiceBay"] = relationship(back_populates="appointments")

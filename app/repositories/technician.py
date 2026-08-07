"""Technician repository - persistence access only, no business rules."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.technician import Technician
from app.repositories.base import BaseRepository


class TechnicianRepository(BaseRepository[Technician]):
    model = Technician

    def list_by_dealer(self, dealer_id: uuid.UUID) -> list[Technician]:
        """Ordered by `id` so that candidate iteration/locking in
        `BookingService` always visits rows in the same global order
        across concurrent transactions, avoiding lock-order deadlocks
        (ADR-005 amendment)."""
        return list(
            self.db.scalars(
                select(Technician)
                .where(Technician.dealer_id == dealer_id)
                .order_by(Technician.id)
            ).all()
        )

    def lock_for_update(self, id: uuid.UUID) -> Technician | None:
        """Re-fetches the row with `SELECT ... FOR UPDATE` so the caller
        can hold a row lock for the duration of its transaction (see
        ADR-005 amendment). Locking/transaction boundaries themselves are
        owned by the caller, not this repository.
        """
        return self.db.scalars(
            select(Technician).where(Technician.id == id).with_for_update()
        ).first()

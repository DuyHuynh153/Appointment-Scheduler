"""Service Bay repository - persistence access only, no business rules."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.service_bay import ServiceBay
from app.repositories.base import BaseRepository


class ServiceBayRepository(BaseRepository[ServiceBay]):
    model = ServiceBay

    def list_by_dealer(self, dealer_id: uuid.UUID) -> list[ServiceBay]:
        """Ordered by `id` so that candidate iteration/locking in
        `BookingService` always visits rows in the same global order
        across concurrent transactions, avoiding lock-order deadlocks
        (ADR-005 amendment)."""
        return list(
            self.db.scalars(
                select(ServiceBay)
                .where(ServiceBay.dealer_id == dealer_id)
                .order_by(ServiceBay.id)
            ).all()
        )

    def lock_for_update(self, id: uuid.UUID) -> ServiceBay | None:
        """Re-fetches the row with `SELECT ... FOR UPDATE` (see
        ADR-005 amendment). Locking/transaction boundaries themselves are
        owned by the caller, not this repository.
        """
        return self.db.scalars(
            select(ServiceBay).where(ServiceBay.id == id).with_for_update()
        ).first()

"""Vehicle repository - persistence access only, no business rules."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.vehicle import Vehicle
from app.repositories.base import BaseRepository


class VehicleRepository(BaseRepository[Vehicle]):
    model = Vehicle

    def get_by_vin(self, vin: str) -> Vehicle | None:
        return self.db.scalars(select(Vehicle).where(Vehicle.vin == vin)).first()

    def list_by_dealer(self, dealer_id: uuid.UUID) -> list[Vehicle]:
        return list(
            self.db.scalars(select(Vehicle).where(Vehicle.dealer_id == dealer_id)).all()
        )

    def lock_for_update(self, id: uuid.UUID) -> Vehicle | None:
        """Re-fetches the row with `SELECT ... FOR UPDATE` so the caller
        can hold a row lock for the duration of its transaction (see
        ADR-005 amendment, which extends locking to vehicles). Locking/
        transaction boundaries themselves are owned by the caller, not
        this repository.
        """
        return self.db.scalars(
            select(Vehicle).where(Vehicle.id == id).with_for_update()
        ).first()

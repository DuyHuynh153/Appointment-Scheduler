"""Dealer repository - persistence access only, no business rules."""
from __future__ import annotations

from app.models.dealer import Dealer
from app.repositories.base import BaseRepository


class DealerRepository(BaseRepository[Dealer]):
    model = Dealer

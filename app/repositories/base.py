"""Generic base repository - shared persistence primitives only.

No business rules and no transaction orchestration live here (see
IMPLEMENTATION_PLAN.md Section 7): repositories only translate
method calls into SQLAlchemy statements against an injected
`Session`. Commit/rollback/transaction boundaries are owned by
callers (the future `BookingService`), not by repositories.
"""
from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Common CRUD primitives for a single ORM model.

    Subclasses set `model` and add entity-specific query methods; they
    should not add validation or multi-step orchestration logic.
    """

    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        return self.db.get(self.model, id)

    def list_all(self) -> list[ModelT]:
        return list(self.db.scalars(select(self.model)).all())

    def add(self, instance: ModelT) -> ModelT:
        """Stages `instance` for insert and flushes so its generated
        columns (id, timestamps) are populated. Does not commit -
        commit/rollback is the caller's responsibility.
        """
        self.db.add(instance)
        self.db.flush()
        return instance

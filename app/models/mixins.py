"""Shared mixins for ORM models: UUIDv7 primary key + timestamps.

Kept here (persistence shape only, no business logic) rather than in
`app/db/base.py` so `Base` itself stays a plain declarative base and
these are opt-in per model.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.uuid import uuid7


class UUIDPrimaryKeyMixin:
    """Adds a UUIDv7 primary key column named `id`."""

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid7
    )


class TimestampMixin:
    """Adds `created_at` / `updated_at` columns (see Domain Model Review,
    2026-08-07: `updated_at` added to all mutable entities)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

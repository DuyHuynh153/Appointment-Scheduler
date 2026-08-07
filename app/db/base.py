"""Declarative base for all SQLAlchemy ORM models.

TODO: model modules under `app/models/` should import `Base` from here
and inherit from it to register their tables. No models are defined
yet - see `app/models/__init__.py`.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base class for all ORM models."""

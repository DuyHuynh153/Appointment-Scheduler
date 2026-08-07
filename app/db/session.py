"""SQLAlchemy engine/session setup (sync engine - see ADR-001 amendment).

Provides the process-wide `Engine` + `sessionmaker`, plus a `get_db`
FastAPI dependency that yields a request-scoped session and guarantees
it is closed (and rolled back on error) afterward.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,
    # Pin every connection's session timezone to UTC explicitly rather
    # than relying on the Postgres server/container default
    # (IMPLEMENTATION_PLAN.md Section 4: "all timestamps stored/
    # compared in UTC"). This makes timezone-sensitive operations
    # (e.g. `date()` casts on `timestamptz` columns) correct regardless
    # of how the Postgres server itself is configured.
    connect_args={"options": "-c timezone=UTC"},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped DB session.

    Rolls back on exception and always closes the session, so route
    handlers/services never manage session lifecycle directly.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

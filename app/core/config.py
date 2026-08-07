"""Environment-driven application settings.

See docs/ADR/ADR-004.md for the feature-toggle rationale and
IMPLEMENTATION_PLAN.md Section 12 for the full settings contract.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings.

    All fields can be overridden via environment variables (or a `.env`
    file - see `.env.example`). Application code should depend on
    `Settings` via `get_settings()`, not read `os.environ` directly.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application metadata ---
    app_name: str = "Appointment Scheduler API"
    version: str = "1.0.0"
    environment: str = "local"

    # --- Database (sync SQLAlchemy 2 engine, psycopg driver - see
    # ADR-001 amendment) ---
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/appointments",
        description="Sync SQLAlchemy connection string (psycopg driver).",
    )
    db_echo: bool = False

    # --- Logging (see core/logging.py) ---
    log_level: str = "INFO"

    # --- Feature toggles (see ADR-004) ---
    enable_auto_assign: bool = True
    enable_overlap_validation: bool = True
    enable_structured_logging: bool = True

    # --- Business rules constants (see IMPLEMENTATION_PLAN.md Section 4:
    # system-wide fixed business hours, not per-dealer configurable) ---
    business_hours_start: str = "08:00"
    business_hours_end: str = "18:00"

    # --- Observability (see ADR-003) ---
    correlation_id_header: str = "X-Correlation-ID"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached `Settings` instance.

    Cached so settings are read from the environment once at startup
    (ADR-004: toggles are process-wide, not per-request) and so
    FastAPI's dependency injection can share a single instance.
    """
    return Settings()

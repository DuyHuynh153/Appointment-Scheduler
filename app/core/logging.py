"""Structured logging configuration.

Configures `structlog` so every application log line goes through the
same processor chain and, when `ENABLE_STRUCTURED_LOGGING` is on, is
rendered as JSON.

See ADR-003 for the `correlation_id` vs `request_id` distinction and
IMPLEMENTATION_PLAN.md Section 12 for the required per-request log
fields (request_id, correlation_id, method, path, status, duration_ms,
user_agent, response_size). Those fields are bound to each request's
logger by the correlation-id/request-logging middleware - see
`app/core/middleware.py` (not yet implemented).
"""
import logging
import sys
from typing import Any

import structlog

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure the stdlib logging root handler + structlog processors.

    Call this once at application startup (see `app/main.py`).
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level.upper(),
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer: Any = (
        structlog.processors.JSONRenderer()
        if settings.enable_structured_logging
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """Return a structlog logger, typically bound to `__name__`.

    TODO: once `app/core/middleware.py` is implemented, per-request
    fields (correlation_id, request_id) will be bound via
    `structlog.contextvars.bind_contextvars(...)` for the duration of
    each request rather than passed manually at each call site.
    """
    return structlog.get_logger(name)

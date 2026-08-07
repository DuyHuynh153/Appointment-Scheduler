"""Small shared time helpers.

Extracted so `BookingService` and `AvailabilityService` share the same
"HH:MM" business-hours parsing logic instead of duplicating it (see
IMPLEMENTATION_PLAN.md Section 4: fixed, system-wide business hours).
"""
from __future__ import annotations

from datetime import datetime, time, timezone


def parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))


def to_utc(value: datetime) -> datetime:
    """Normalizes `value` to an offset-aware UTC `datetime`.

    Enforces IMPLEMENTATION_PLAN.md Section 4's "single timezone for
    the whole system... all timestamps stored/compared in UTC"
    assumption at the boundary: a naive `datetime` is rejected (it is
    ambiguous - the caller's intended offset is unknown), and any
    offset-aware `datetime` is converted to UTC.
    """
    if value.tzinfo is None:
        raise ValueError(
            "datetime must be timezone-aware (e.g. include a UTC offset or 'Z' suffix); "
            "naive/ambiguous timestamps are not accepted."
        )
    return value.astimezone(timezone.utc)

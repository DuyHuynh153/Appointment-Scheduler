"""UUIDv7 generation helper for ORM primary keys.

See IMPLEMENTATION_PLAN.md Section 11: UUIDv7 primary keys are
preferred (sortable by creation time, better index locality than
UUIDv4); UUIDv4 is an explicitly-acceptable fallback since the
overlap/locking logic doesn't depend on key ordering, only on
correctness. Implemented here directly (RFC 9562 layout) rather than
pulling in a new dependency for a one-week assessment.
"""
import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7: 48-bit unix ms timestamp + random bits.

    Layout (128 bits): 48 bits unix_ts_ms | 4 bits version (0111) |
    12 bits rand_a | 2 bits variant (10) | 62 bits rand_b.
    """
    unix_ts_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF

    value = (
        (unix_ts_ms << 80)
        | (0x7 << 76)
        | (rand_a << 64)
        | (0b10 << 62)
        | rand_b
    )
    return uuid.UUID(int=value)

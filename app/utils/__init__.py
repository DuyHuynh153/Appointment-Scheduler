"""Small shared helpers.

`uuid7()` (see `app.utils.uuid`) is used as the default primary-key
generator for all ORM models - see `app/models/mixins.py`.

TODO: time-window overlap math shared by overlap-checking
queries/tests (half-open interval `[start, end)` semantics - see
Domain Model Review, 2026-08-07). Not implemented yet.
"""

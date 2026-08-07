"""Database package: engine/session setup and the declarative base.

Import `Base` from `app.db.base` when defining ORM models (see
`app/models/`, not yet implemented), and `get_db` from
`app.db.session` as a FastAPI dependency (also re-exported via
`app.api.deps`).
"""

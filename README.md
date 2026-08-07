# Appointment Scheduler API

A backend service for managing vehicle service appointments across dealerships.
It auto-assigns technicians and bays, enforces no-overlap invariants under concurrent
load, and is structured to be extended without a rewrite.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI (sync path) + Uvicorn |
| Validation | Pydantic v2 |
| ORM / DB | SQLAlchemy 2 (sync) + PostgreSQL 16 |
| Driver | psycopg (v3) |
| Migrations | Alembic |
| Logging | structlog (JSON) |
| Testing | pytest, in-memory fake repositories |

---

## Architecture

```
Client
  │  HTTP/JSON
  ▼
Middleware          ← correlation ID, request timing, structured access log
  │
API Layer           ← request parsing, Pydantic DTOs, no business logic
  │
Service Layer       ← business rules, transaction boundary (BookingService)
  │
Repository Layer    ← SQLAlchemy queries only, no decisions
  │
PostgreSQL
```

The service layer is framework-agnostic and unit-tested entirely with fake
repositories — no database or running server required for the test suite.

---

## How to Run

```bash
docker compose up --build
```

The API container runs `alembic upgrade head` before starting `uvicorn`, so the
schema is applied automatically on a fresh database. The `api` service declares a
healthcheck against `GET /health`; the compose file waits for Postgres to be
healthy before starting the API.

```bash
# Confirm readiness
curl http://localhost:8000/health
# → {"status": "UP", "database": "UP", "version": "1.0.0"}
```

Interactive API docs: `http://localhost:8000/docs`

### Seed data

Run once after the stack is up to load one dealer, two technicians, two bays, two
vehicles, and three service types with fixed IDs:

```bash
docker compose exec api python scripts/seed.py
```

The script is idempotent — it skips silently if data already exists.

**Ready-to-use curl example** (book a 30-minute oil change):

```bash
curl -s -X POST http://localhost:8000/api/v1/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "dealer_id":       "10000000-0000-0000-0000-000000000001",
    "vehicle_id":      "40000000-0000-0000-0000-000000000001",
    "service_type_id": "50000000-0000-0000-0000-000000000001",
    "start_time":      "2026-09-15T09:00:00Z"
  }' | python -m json.tool
```

Check availability before booking:

```bash
curl -s "http://localhost:8000/api/v1/availability?\
dealer_id=10000000-0000-0000-0000-000000000001&\
service_type_id=50000000-0000-0000-0000-000000000001&\
date=2026-09-15" | python -m json.tool
```

| Seed entity | ID |
|---|---|
| Dealer — Sunrise Auto | `10000000-0000-0000-0000-000000000001` |
| Vehicle — Jane Doe | `40000000-0000-0000-0000-000000000001` |
| Vehicle — John Smith | `40000000-0000-0000-0000-000000000002` |
| Service Type — Oil Change (30 min) | `50000000-0000-0000-0000-000000000001` |
| Service Type — Tire Rotation (45 min) | `50000000-0000-0000-0000-000000000002` |
| Service Type — Brake Inspection (60 min) | `50000000-0000-0000-0000-000000000003` |

---

## API Summary

All endpoints are under `/api/v1`. Every error uses the shape
`{"code": "...", "message": "...", "correlation_id": "..."}`.

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| `POST` | `/appointments` | Create appointment (backend assigns technician + bay) | 201 | 404, 409, 422 |
| `GET` | `/appointments` | List appointments (`dealer_id` required) | 200 | 404 |
| `GET` | `/appointments/{id}` | Get single appointment | 200 | 404 |
| `DELETE` | `/appointments/{id}` | Cancel appointment (soft delete) | 204 | 404, 409 |
| `GET` | `/availability` | List open slots for dealer + service type + date | 200 | 404 |
| `GET` | `/health` | Liveness + DB connectivity probe | 200 | 503 |

**`POST /appointments` request body:**

```json
{
  "dealer_id": "<uuid>",
  "vehicle_id": "<uuid>",
  "service_type_id": "<uuid>",
  "start_time": "2026-09-15T09:00:00Z"
}
```

`technician_id` and `bay_id` are rejected if supplied — the backend always assigns
them. `start_time` must be timezone-aware; naive timestamps are rejected with `422`.

---

## Key Design Decisions

Full rationale is in `docs/ADR/`. Highlights:

- **Service layer owns the transaction** (ADR-002). `BookingService.create_appointment`
  runs validate → lock → overlap check → insert atomically. Route handlers contain
  no business logic.

- **`SELECT FOR UPDATE` prevents double-booking** (ADR-005). Candidate technician,
  bay, and vehicle rows are re-locked inside the transaction before the overlap
  check, closing the check-then-act race window. Candidates are fetched in primary
  key order to prevent deadlocks between concurrent transactions.

- **Overlap uses half-open intervals** `[start, end)`. Two adjacent appointments
  whose end and start times are equal are not considered overlapping — by design.

- **UTC enforced at two boundaries**. Naive `start_time` values are rejected at the
  API schema layer. The SQLAlchemy engine pins every connection to
  `SET timezone=UTC`, so PostgreSQL date casts behave correctly regardless of the
  server's default timezone.

- **Soft cancellation** (ADR-006). `DELETE` transitions `status → CANCELLED`; the
  row is never physically deleted. Required by the 409-on-repeat-cancel contract
  and preserves booking history without a separate audit table.

- **Structured logging + correlation IDs** (ADR-003). Every request carries a
  `correlation_id` (propagated from `X-Correlation-ID` or generated) and a fresh
  `request_id`. Both appear on every log line; `correlation_id` is echoed in the
  response header, ready for cross-service tracing.

- **Synchronous FastAPI / SQLAlchemy** (ADR-001 amendment). Sync session handling
  and test fixtures are simpler at this scale. Nothing in the requirements benefits
  from async I/O.

---

## Trade-offs / Assumptions

| Decision | Rationale |
|---|---|
| Single system-wide timezone (UTC) | Keeps logic simple; per-dealer timezone is the documented next step |
| Appointment duration fixed by `service_type.duration_minutes` | Prevents client manipulation of scheduling windows |
| No authentication | Out of scope; a half-implemented auth layer is worse than a documented gap |
| No `notes` field | No DB column was added within scope; intentional omission, not an oversight |
| `GET /availability` is a snapshot | Returned slots are informational and do not lock resources; the booking endpoint enforces the real invariant |

---

## Future Improvements

- **Schema-level overlap enforcement** — replace `SELECT FOR UPDATE` with a
  `EXCLUDE USING gist (technician_id WITH =, tstzrange(start_time, end_time) WITH &&)`
  constraint so the invariant is impossible to violate from any code path (ADR-005).
- **Per-dealer configurable business hours** — the `dealers.timezone` column and
  `BUSINESS_HOURS_*` settings are the natural extension points.
- **Authentication** — JWT middleware with dealer-scoped claims.
- **Pagination** — `GET /appointments` and `GET /availability` return unbounded sets.
- **Metrics / tracing** — OpenTelemetry once there is multi-instance traffic.

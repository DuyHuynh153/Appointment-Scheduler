"""Correlation ID + structured request logging middleware.

TODO (Phase 5 - Observability, see IMPLEMENTATION_PLAN.md Section 12
and ADR-003):
- Read `X-Correlation-ID` from the incoming request, or generate one
  (e.g. UUIDv4) if absent.
- Generate a fresh `request_id` for every request (never reused, even
  across retries of the "same" logical call).
- Bind both onto structlog's contextvars for the duration of the
  request so every log line emitted while handling it includes them.
- Time the request and emit one structured access log line on the way
  out with: request_id, correlation_id, method, path, status,
  duration_ms, user_agent, response_size.
- Echo `X-Correlation-ID` back on the response.
- Register the middleware on the app in `app/main.py`.

Not implemented yet - this module is a placeholder so the import path
(`app.core.middleware`) is stable once wired in.
"""

# TODO: implement CorrelationIdMiddleware / request logging middleware.

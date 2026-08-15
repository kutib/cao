# Logging

Logs answer "what exactly happened to this one request". Metrics answer "how is the
system doing" and traces answer "where did the time go". Using logs for the other two
jobs is expensive and slow.

## Format

Structured JSON to stdout. One event per line. Applications never write log files
inside a container — the platform collects stdout.

Every line carries:

| Field | Notes |
| --- | --- |
| `timestamp` | RFC 3339, UTC |
| `level` | `DEBUG` / `INFO` / `WARN` / `ERROR` |
| `message` | Fixed, low-cardinality text; variables go in fields |
| `service.name`, `service.version` | Matching the OTel resource attributes exactly |
| `trace_id`, `span_id` | So a line pivots to its trace and back |
| `correlationId` | The same value returned in error responses |

**The message is a constant; the data is in fields.** `"order not found"` with
`{orderId: 8812}` is greppable and groupable. `"order 8812 not found"` is neither,
and every line is unique.

## Levels

- **ERROR** — something failed that a human may need to act on. Every ERROR should be
  something you would want to see in a daily review. If a class of ERROR is routinely
  ignored, it is a WARN or it is noise.
- **WARN** — degraded but handled: a retry succeeded, a fallback was used, a
  deprecated endpoint was called.
- **INFO** — significant business or lifecycle events: started, stopped,
  configuration loaded, order placed. Not one per function call.
- **DEBUG** — off in production, enabled deliberately and temporarily.

Levels are configurable at runtime without a redeploy, ideally per logger. During an
incident, the ability to raise one component to DEBUG for ten minutes is worth a
great deal.

## Log once

An error is logged **once**, at the boundary where it becomes a response or is
finally handled. Logging at every layer as it propagates turns one failure into six
lines, makes error counts meaningless, and buries the one line with the useful
context.

Corollary: a `catch` that logs and rethrows is almost always wrong. Either handle it
or let it propagate.

## What never goes in a log

Passwords · tokens · API keys · session identifiers · full payment card data ·
personal data beyond what `data-classification.md` permits · full request or response
bodies on anything carrying user data · authorization headers · connection strings
with credentials.

Redact at the source. A redaction rule in the collector is a safety net, not a
control — it silently stops working when a field is renamed.

Logging an entire request object "for debugging" is how personal data ends up in a
log store with a two-year retention and no deletion path.

## Volume

Log volume is a cost and a signal-to-noise problem, and the two compound: the service
that logs most is usually the one hardest to debug.

- No logging inside hot loops or per-item in a batch. Log the batch outcome.
- No logging of successful health checks.
- Sample high-volume INFO lines if they are needed at all.
- A retry that succeeds is one WARN at the end, not one per attempt.
- If a line is emitted more than a few times per request, it is a metric or a span
  attribute, not a log.

## What is worth logging

- Service lifecycle: start with the resolved configuration (secrets redacted), and
  shutdown.
- Every authentication failure, authorization denial, and privileged action —
  enough to investigate, no more than needed.
- Business events that would otherwise be unreconstructable: state transitions,
  external side effects, money movement.
- The final failure of a retried operation, with the attempt count and the reason.
- Anything sent to a dead-letter destination.
- Configuration or feature-flag changes taking effect.

## Correlation

The `trace_id` in a log line is what makes the whole system navigable: a user
complaint yields a correlation ID, which yields a trace, which yields every log line
across every service for that request. This only works if:

- Trace context propagates across HTTP and message boundaries — see
  `../stack/opentelemetry.md`.
- The logging framework injects the active trace context automatically. Doing it
  manually means it is missing exactly where it was needed.
- Asynchronous work — thread pools, schedulers, message handlers — carries the
  context forward rather than starting fresh.

## Retention

Set deliberately per environment, and short by default. Long retention on logs
carrying personal data creates a deletion obligation nobody planned for; see
`data-classification.md`. Aggregate what needs long-term retention into metrics
instead.

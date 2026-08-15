# Error semantics

One error shape across every service in the organization. Consistency here is worth
more than elegance: client error handling, dashboards, and alerting all depend on it.

## The shape

```json
{
  "error": {
    "code": "ORDER_ALREADY_CANCELLED",
    "message": "Order 8812 has already been cancelled and cannot be cancelled again.",
    "correlationId": "01J9F2K3M4N5P6Q7R8S9T0",
    "details": [
      { "field": "quantity", "code": "OUT_OF_RANGE", "message": "Must be between 1 and 100." }
    ]
  }
}
```

- **`code`** — stable, machine-readable, `SCREAMING_SNAKE_CASE`. This is part of the
  contract: clients branch on it, so changing it is a breaking change. Never
  renumber or reuse codes.
- **`message`** — for a human reading a log or a support ticket. It may change
  freely; nothing should parse it.
- **`correlationId`** — the same ID that appears in the logs and traces for this
  request. This is what turns a user's screenshot into a five-minute investigation.
- **`details`** — optional, for field-level validation failures. All of them, not
  just the first: a form that reveals one error per submission is a bad API.

## Classify before responding

Every error is one of three kinds, and the kind determines the status code:

1. **The caller can fix it.** Bad input, missing permission, wrong state. `4xx`. The
   message must say what to do differently.
2. **The caller can retry it.** Transient unavailability, timeout, rate limit. `429`,
   `503`, or `504`, always with `Retry-After` when a sensible value exists.
3. **The caller can do nothing.** A genuine defect. `500`, a generic message, and a
   correlation ID. The detail goes to the logs.

Misclassifying kind 3 as kind 1 sends clients chasing their own code. Misclassifying
kind 1 as kind 3 fills your error budget with other people's bugs.

## What never goes in an error response

Stack traces, SQL or Mongo queries, internal hostnames, file paths, library versions,
raw exception messages from a dependency, other users' data, or anything that
distinguishes "this resource does not exist" from "this resource exists and is not
yours" when that distinction is itself sensitive.

## Retry signalling

- `429` and `503` include `Retry-After`.
- Errors that must never be retried — validation failures, permission denials — must
  be unambiguous, or well-behaved clients will retry them anyway and turn a bad
  request into a load problem.
- Document, per endpoint, which failures are safe to retry. Combined with the
  `Idempotency-Key` support in `api-rest.md`, this is what makes client retries safe.

## Errors across asynchronous boundaries

A failed message has no caller to answer. The equivalent contract is:

- The failure reason, the original message, the consumer, and the attempt count go to
  the dead-letter destination as headers — see `api-async-events.md`.
- The correlation and trace IDs travel with it, so the DLQ entry can be tied back to
  the originating request.
- A permanent failure is distinguished from a transient one *before* the retry
  budget is spent. Retrying a malformed message thirty times is thirty times the load
  for the same outcome.

## Errors and observability

- Every error response sets its span status to Error and records the exception —
  `../stack/opentelemetry.md`.
- Every error is logged once, at the boundary where it becomes a response. Logging it
  at every layer on the way up turns one failure into six alerts and makes error
  rates meaningless.
- The `code` field is a low-cardinality metric label; the `correlationId` is not.
  Never label a metric with it — see `metrics-naming.md`.

## Language

Error messages are written for the person who will read them at 3am. State what
happened and what to do about it. "An error occurred" tells nobody anything, and
"Invalid input" is barely better than silence.

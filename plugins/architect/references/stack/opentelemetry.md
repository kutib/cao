# OpenTelemetry standards

Collector endpoint and backends live in `../org-profile.md`.

OpenTelemetry is the only instrumentation API used. Vendor-specific SDKs are not
introduced without an ADR — the point of a single API is that the backend can change
without touching application code.

## Resource attributes

Every signal — trace, metric, log — carries the same resource attributes, or they
cannot be correlated. Set these once at startup:

| Attribute | Value |
| --- | --- |
| `service.name` | the service's stable name, identical across environments |
| `service.version` | the deployed version or image digest |
| `service.namespace` | the owning domain or team |
| `deployment.environment` | dev / staging / prod |
| `k8s.namespace.name`, `k8s.pod.name` | from the downward API |

`service.name` is the join key for everything. If it differs between traces and
metrics, dashboards silently show nothing.

## Traces

**Span per unit of work that can fail or be slow.** Not per function call — a trace
with 400 spans per request is unreadable and expensive.

Instrument, at minimum:

- Every inbound entry point (HTTP handler, message consumer, scheduled job).
- Every outbound call (HTTP client, MongoDB, Elasticsearch, Kafka, RabbitMQ).
- Any in-process step that takes meaningful time or has its own failure mode.

**Naming.** Low cardinality. `GET /orders/{id}`, never `GET /orders/12345`. High
cardinality span names destroy the backend's index and your query performance.

**Attributes.** Use semantic conventions (`http.request.method`, `db.system`,
`messaging.system`, `server.address`) rather than inventing names — the backend's
built-in views depend on them. Add business identifiers as attributes
(`order.id`, `tenant.id`) so a trace can be found from a support ticket. Never put
secrets, tokens, passwords, or personal data in attributes.

**Errors.** Set the span status to Error and record the exception. A span that
returns a 500 but carries status Unset is invisible to every error dashboard.

## Context propagation

- **W3C `traceparent`** across HTTP. This is not optional; a broken chain turns one
  trace into several disconnected ones.
- **Message headers** across Kafka and RabbitMQ. The consumer creates a span with a
  **link** to the producer's span rather than a parent-child relationship — the work
  is asynchronous and may happen hours later. A consumer span parented to a producer
  span produces traces that appear to last for hours.
- Propagate through every asynchronous boundary inside the process too: thread pools,
  queues, and scheduled executors lose context unless it is carried explicitly.

## Sampling

- Head sampling at the configured default rate, **with all errors and all slow
  requests sampled**. A trace backend full of successful fast requests is the least
  useful sample possible.
- Sampling decisions propagate — a service that re-decides breaks traces in half.
- Health-check and metrics endpoints are excluded from tracing entirely.

## Metrics

Emit through the OTel metrics API. Naming, units, and cardinality rules are in
`../standards/metrics-naming.md`; what to measure and alert on is in
`../standards/slo-catalog.md`.

The rule that matters most: **attributes must be low cardinality.** A metric labelled
with a user ID, an order ID, or a raw URL path will take out the metrics backend.
That detail belongs on a span, not on a counter.

## Logs

Structured JSON to stdout, carrying `trace_id` and `span_id` so a log line can be
pivoted to its trace and back. Full rules in `../standards/logging.md`.

## Collector

Applications export to the cluster collector, not directly to a backend. The
collector handles batching, retry, redaction, and routing, and it means changing
backends does not require redeploying every service.

Export failures must not block the application or fill memory without bound. Verify
that the SDK is configured to drop rather than stall when the collector is
unreachable — an observability outage should not become a service outage.

## Verifying instrumentation

Instrumentation is not done when the code compiles. Before go-live:

1. Trigger a request and follow one complete trace end to end across every service.
2. Trigger a failure and confirm the error span appears with its status set.
3. Confirm a message crossing Kafka or RabbitMQ links producer to consumer.
4. Confirm a log line can be pivoted to its trace and back.

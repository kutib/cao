---
name: observability-plan
description: Plan OpenTelemetry instrumentation for a service — the spans it emits, resource attributes, context propagation across HTTP and message boundaries, structured logs correlated to traces, sampling, and how the instrumentation gets verified. Use when building a new service, adding a component to a flow, when an incident was hard to diagnose, or before a production readiness review.
when_to_use: Triggered by "observability", "add tracing", "OpenTelemetry", "OTel", "instrument this", "we couldn't debug that incident", "correlate logs and traces", "sampling", or "what should we log".
argument-hint: [service or flow]
---

# Observability plan

Subject: `$ARGUMENTS`

Standards: `${CLAUDE_PLUGIN_ROOT}/references/stack/opentelemetry.md` and
`${CLAUDE_PLUGIN_ROOT}/references/standards/logging.md`.
Backends and the collector endpoint: `${CLAUDE_PLUGIN_ROOT}/references/org-profile.md`.

Metrics and alerting are a separate concern — `/architect:metrics-strategy` owns
them. This skill covers traces and logs.

## 1. Start from the question you will need to answer

Instrumentation designed from "what can we emit" produces data nobody uses.
Instrumentation designed from "what will we need to know at 3am" produces a system
you can debug.

Write down the three or four questions first. Typically:

- A user reports that request X was slow or failed — where did the time go, and what
  failed?
- A consumer is lagging — is it slow processing, a slow dependency, or a stalled
  partition?
- Error rate rose after a deploy — which change, and which code path?
- Data is missing downstream — where in the chain did it stop?

Every instrumentation decision below is justified by one of these.

## 2. Resource attributes

Set once at startup, identically across traces, metrics, and logs, or nothing
correlates: `service.name`, `service.version`, `service.namespace`,
`deployment.environment`, plus the Kubernetes pod and namespace from the downward
API.

`service.name` is the join key for the entire observability stack. A mismatch between
signals produces dashboards that are silently empty.

## 3. Spans

A span per unit of work that can fail or be slow — not per function call. Cover:

- Every inbound entry point: HTTP handler, message consumer, scheduled job.
- Every outbound call: HTTP, MongoDB, Elasticsearch, Kafka, RabbitMQ.
- Any in-process step with meaningful duration or its own failure mode.

**Names are low cardinality.** `GET /orders/{id}`, never with the ID interpolated.

**Attributes** follow the semantic conventions — `http.request.method`, `db.system`,
`messaging.system` — because the backend's built-in views depend on them. Add
business identifiers (`order.id`, `tenant.id`) so a trace is findable from a support
ticket. This is where high-cardinality context belongs; never on a metric.

**Errors** set the span status to Error and record the exception. A failing span left
at status Unset is invisible to every error view.

**Never** put secrets, tokens, or personal data in attributes — see
`${CLAUDE_PLUGIN_ROOT}/references/standards/data-classification.md`.

## 4. Propagation — the part that is usually broken

- W3C `traceparent` across HTTP, in both directions.
- Trace context in Kafka and RabbitMQ message headers. The consumer span carries a
  **link** to the producer span rather than being its child — asynchronous work may
  happen hours later, and parenting it produces traces that appear to last for hours.
- In-process asynchronous boundaries: thread pools, executors, schedulers, and
  message handlers all lose context unless it is carried explicitly.

A broken chain turns one trace into several disconnected ones, which is worse than no
tracing because it looks like it works.

## 5. Logs

Structured JSON to stdout, with `trace_id` and `span_id` injected automatically by
the logging framework. Log an error once, at the boundary where it becomes a
response. Constant messages with variables in fields.

Decide explicitly what is *not* logged: successful health checks, per-item lines in
batches, per-attempt retry lines, and anything carrying personal data.

## 6. Sampling

Head sampling at the org default, **with all errors and all slow requests always
sampled**. The sampling decision propagates — a service that re-decides breaks traces
in half. Health and metrics endpoints are excluded from tracing entirely.

Export failures must drop rather than stall or buffer without bound. An observability
outage must not become a service outage.

## 7. Decision checkpoints

Use `AskUserQuestion` for:

- Sampling rate, where the default does not fit the volume or the debugging need
- Adding a high-cost instrumentation path (per-item spans in a bulk pipeline)
- Emitting anything derived from classified data into telemetry

## 8. Verify — instrumentation is not done when it compiles

The plan must include these four checks, run before go-live:

1. Trigger a request and follow one complete trace end to end across every service.
2. Trigger a failure and confirm the error span appears with its status set.
3. Send a message through Kafka or RabbitMQ and confirm producer and consumer are
   linked.
4. Take one log line and pivot to its trace, then back.

Untested instrumentation is discovered to be broken during the incident it was built
for.

## 9. Output

Add an observability section to the design document, or write
`docs/architecture/<slug>/observability.md`. It lists: the questions being designed
for, the span inventory, the propagation points, the log events, the sampling
decision, and the four verification steps with their results.

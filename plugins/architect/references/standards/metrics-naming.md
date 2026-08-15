# Metric naming and cardinality

Metrics are cheap in aggregate and ruinously expensive per unique label combination.
Almost every metrics outage in a system like this is a cardinality accident.

## Naming

`<namespace>_<subject>_<unit>[_total]`, lower snake case.

- `http_server_request_duration_seconds`
- `kafka_consumer_lag_seconds`
- `orders_placed_total`
- `mongodb_connection_pool_in_use`

Rules:

- **Units in the name, base units only.** Seconds, not milliseconds. Bytes, not
  megabytes. A metric named `_duration` with no unit will be misread by someone
  building a dashboard at 2am.
- **Counters end in `_total`** and only ever increase. A counter that resets on
  deploy is fine; rate functions handle it. A counter that decreases is a gauge with
  a misleading name.
- Name the thing measured, not the alert you plan to build.
- Consistency across services beats local elegance — a dashboard spanning services
  needs the same metric name in each.

## The three instrument types

- **Counter** — monotonic totals: requests, errors, messages processed. Query with
  `rate()`; never graph the raw value.
- **Gauge** — a current level that can go up or down: queue depth, connections in
  use, in-flight requests.
- **Histogram** — a distribution, for latency and sizes. Buckets are chosen to
  straddle the SLO threshold: a histogram whose buckets are 0.1/1/10 seconds cannot
  tell you whether you met a 300 ms target.

**Never compute an average latency and alert on it.** An average hides exactly the
tail that users experience. Use percentiles from a histogram — and remember that
percentiles cannot be averaged across instances, which is why the histogram must be
aggregated before the quantile is computed.

## Cardinality — the rule that matters

Total series = product of all label value counts, per metric, per service instance.
Three labels of 10, 20, and 50 values is 10,000 series from one metric.

**Never use as a label:**

user ID · order ID · session ID · request ID · trace ID · correlation ID · email
address · IP address · raw URL path with identifiers in it · full error message ·
timestamp · any free-text field · any unbounded external input

**Safe labels:** service, environment, endpoint **template** (`/orders/{id}`),
HTTP method, status class, error code from a fixed set, topic name, queue name,
consumer group, dependency name.

The test: *can I enumerate every possible value of this label right now, and is that
list under about fifty?* If not, it is not a label.

High-cardinality context belongs on a **span**, not on a metric. That is what
tracing is for — see `../stack/opentelemetry.md`.

## Every service exports these

The baseline set, so cross-service dashboards work without per-service special cases:

**RED, for every inbound entry point:**
- `<ns>_requests_total{endpoint, method, status_class}`
- `<ns>_request_errors_total{endpoint, error_code}`
- `<ns>_request_duration_seconds` (histogram, by endpoint)

**For every outbound dependency:**
- `<ns>_dependency_requests_total{dependency, outcome}`
- `<ns>_dependency_duration_seconds{dependency}`
- `<ns>_dependency_retries_total{dependency}`

**For every consumer:**
- `<ns>_messages_consumed_total{topic, outcome}`
- `<ns>_message_processing_duration_seconds{topic}`
- `<ns>_consumer_lag_seconds{topic, group}`
- `<ns>_dlq_messages_total{topic}`

**USE, for saturating resources:** connection pool in use versus capacity, thread
pool queue depth, memory, and anything else with a hard ceiling that will be hit.

**Build info:** a gauge of value 1 labelled with version, so a graph can be
correlated with a deploy.

## Anti-patterns

- A metric per customer, per tenant, or per endpoint instance. That is a log or a
  span.
- Alerting on a raw counter rather than its rate.
- A gauge sampled so rarely it misses the spike it exists to catch.
- Recording both a metric and a log line for every request purely to compute the
  same number two ways.
- Adding a label "just in case" — every label is permanent in practice, because
  removing one breaks every dashboard and alert that groups by it.

What to build **on top** of these metrics — SLIs, SLOs, and alerts — is in
`slo-catalog.md`.

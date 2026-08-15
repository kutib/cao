# Kafka standards

Applies to every topic on the on-premise clusters. Cluster-specific values live in
`../org-profile.md`.

## Topics

**Naming.** `<domain>.<entity>.<event>.v<major>` — for example
`orders.order.placed.v1`. Lower case, dots as separators. The major version is part
of the name: an incompatible schema change creates a new topic, it does not mutate
an existing one.

**A topic is a public contract.** Once another team consumes it, its schema, its
key, and its partition count are frozen in practice. Treat creating one with the
same seriousness as publishing an API. See `../standards/api-async-events.md`.

**Partitions.** Choose from throughput and required parallelism, not from a default.

- Partition count is the ceiling on consumer parallelism within a group.
- Increasing partitions later breaks key-based ordering, because existing keys
  rehash to different partitions. Plan for growth up front.
- Rule of thumb: `max(peak_throughput / per_consumer_throughput, target_parallelism)`,
  rounded up, then add headroom. Do not "just use 50" — every partition costs file
  handles, memory, and rebalance time.

**Replication.** Replication factor 3 with `min.insync.replicas=2` for anything that
matters. Producers use `acks=all`. Any lower setting is a decision that needs an ADR
stating the data loss it accepts.

**Retention.** Set deliberately per topic. Defaults are a trap: seven days is not a
policy, it is a coincidence. Decide from the slowest consumer's recovery time plus
the longest planned outage, and from any legal retention limit. Compacted topics for
state-like data (latest value per key); time-based retention for event streams.

## Keys and ordering

- Key by the entity whose ordering matters — order ID, customer ID, account ID.
- A null key means round-robin and no ordering guarantee. That is a valid choice,
  but it must be a choice.
- Never key by something with extreme skew (for example, a tenant ID where one
  tenant is 80% of traffic). A hot partition is a hot consumer and cannot be scaled
  around.

## Producers

- `acks=all`, `enable.idempotence=true`. Idempotent producers are cheap and remove
  duplicate-on-retry.
- Set `max.in.flight.requests.per.connection=5` or lower with idempotence enabled to
  preserve ordering on retry.
- Bound `delivery.timeout.ms` and decide what the application does when it expires.
  Silently dropping is not a decision.
- Transactions only when a write to Kafka must be atomic with another Kafka write.
  Do not reach for them to coordinate Kafka with MongoDB — that is the outbox
  pattern's job.

## Consumers

- **Consumer group naming:** `<service-name>` or `<service-name>-<purpose>`. One
  group per logical consumer. Never share a group across services.
- **Delivery is at-least-once.** Design every handler to be idempotent — a natural
  key with a conditional write, or an explicit processed-message table. Exactly-once
  across Kafka and a database does not exist without an outbox or transactional
  sink; assuming it does is the most common source of duplicate records.
- Commit offsets **after** the work is durable, never before.
- Set `max.poll.interval.ms` above the worst-case processing time for a batch, or
  the consumer is evicted mid-work and the batch is reprocessed forever.
- Prefer cooperative rebalancing (`CooperativeStickyAssignor`) to avoid stop-the-world
  pauses on every deploy.

## Poison messages and retries

Kafka has no per-message redelivery. A failing message blocks its partition. Decide
the strategy per topic and write it in the design:

1. **Retry in place** with backoff, for transient failures — bounded, then escalate.
2. **Retry topic** (`<topic>.retry`) with delayed consumption, for failures likely to
   resolve.
3. **Dead-letter topic** (`<topic>.dlq`) carrying the original message plus the
   failure reason, offset, and timestamp headers.
4. **Skip and alert** — only for data that is genuinely disposable.

Every DLQ needs an owner, an alert on non-zero depth, and a documented drain
procedure. A DLQ nobody looks at is data loss with extra steps.

## Consumer lag

Lag is the primary health signal for a consumer. Alert on **lag in time**
(estimated seconds behind) rather than message count — 10,000 messages means
nothing without a rate. See `../standards/slo-catalog.md`.

## Schema

- Schemas are versioned and compatibility-checked. Backward compatibility is the
  default: a new consumer must be able to read old messages.
- Adding an optional field is safe. Removing a field, renaming one, changing a type,
  or tightening a constraint is a breaking change and means a new major topic.
- Every message carries an envelope: event ID, event type, schema version, occurred-at
  timestamp, producer, and trace context. See `../standards/api-async-events.md`.

## Operating on OpenShift

- Consumers are ordinary Deployments; replica count should not exceed partition
  count, since extra replicas idle.
- Trace context propagates in message headers — see `opentelemetry.md`. A consumer
  span links to the producer span rather than being its child, because the causal
  relationship is asynchronous.
- Graceful shutdown must stop polling, finish in-flight work, and commit, all inside
  `terminationGracePeriodSeconds`. Getting this wrong is why deploys cause duplicate
  processing.

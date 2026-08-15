# RabbitMQ standards

Applies to the on-premise clusters. Cluster-specific values live in
`../org-profile.md`.

## When RabbitMQ is the right choice

See `messaging-choice.md`. Short version: task distribution, per-message routing,
per-message acknowledgement, RPC-shaped interactions, and delayed delivery.

## Queues

**Naming.** `<domain>.<purpose>` for queues, `<domain>.<pattern>` for exchanges —
for example queue `billing.invoice-generation`, exchange `billing.events`. Be
consistent within a domain; the convention matters less than the consistency.

**Quorum queues by default.** Classic mirrored queues are deprecated and lose data
on partition healing. Use quorum queues for anything that must survive a broker
failure. Classic queues are acceptable only for genuinely disposable work, and that
is a decision to state explicitly.

**Durability.** Durable queues plus persistent messages, or the queue is a cache.
Note that durable + persistent still does not guarantee delivery without publisher
confirms.

**Bounded queues.** Set `max-length` or `max-length-bytes` with an overflow policy
of `reject-publish` for work that must not be silently dropped. An unbounded queue
converts a slow consumer into a broker outage.

## Publishers

- **Publisher confirms are mandatory** for anything that matters. Fire-and-forget
  publishing means the application does not know whether the message exists.
- Handle `basic.return` for unroutable messages — a message published to an exchange
  with no matching binding disappears silently otherwise.
- Set a `message_id` and a `correlation_id`, and propagate trace context in headers.

## Consumers

- **Manual acknowledgement.** Auto-ack means a message is lost the instant a
  consumer crashes mid-work. Ack after the work is durable.
- **Set `prefetch` (QoS) explicitly.** The default of unlimited lets one consumer
  grab the whole queue and starve its peers. Start at a small number — 1 for slow,
  long-running tasks; tens for fast ones — and tune from measurement.
- **Idempotency still applies.** Redelivery after a crash is at-least-once. A
  `redelivered` flag is a hint, not a guarantee of first delivery.
- Nack with `requeue=false` for messages that will never succeed, and let the
  dead-letter exchange take them.

## Dead lettering

Every work queue has a dead-letter exchange and a dead-letter queue. Configure
`x-dead-letter-exchange` at declaration time — it cannot be added to an existing
queue without recreating it.

Retry pattern without a plugin: dead-letter to a delay queue with a message TTL,
whose own dead-letter exchange routes back to the original queue. Bound the number
of cycles with a header counter, or a permanently failing message loops forever.

The DLQ needs an owner, an alert on depth, and a drain procedure.

## Routing

- **Direct** for one-to-one by routing key. **Topic** for pattern-based fanout.
  **Fanout** for genuine broadcast. **Headers** only when routing depends on
  multiple attributes — it is slower and harder to reason about.
- Declare topology in code or in migration scripts, not by hand in the management
  UI. Undocumented bindings are the top cause of "messages vanish in production but
  not in staging".

## Connections and channels

- One connection per process, channels per thread. A connection per message is a
  reliable way to exhaust the broker's file descriptors.
- Enable automatic recovery, but verify it: recovery re-declares topology, which
  fails loudly if declarations disagree with what exists.
- Set heartbeats. Without them a half-open connection looks healthy while messages
  go nowhere.

## Sizing and health

Watch these, in this order:

1. **Queue depth and its rate of change** — depth alone is meaningless, growth is
   the signal.
2. **Unacked message count** — a high plateau means consumers are stuck, not slow.
3. **Memory and disk alarms** — when RabbitMQ hits a watermark it blocks publishers,
   which surfaces as unexplained latency in a completely different service.
4. **Consumer count per queue** — a queue with zero consumers and a growing depth is
   an outage in progress.

## Operating on OpenShift

- Consumers scale horizontally; competing consumers on one queue is the intended
  pattern, unlike Kafka.
- Graceful shutdown: stop consuming, finish in-flight messages, ack, then close.
  Cancel the consumer first so the broker stops delivering.
- Do not run the broker's management UI on a public route.

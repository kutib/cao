---
name: reliability-review
description: Work out how a service fails and what it does about it — timeouts, retries with backoff and budgets, idempotency, dead-letter handling, circuit breakers, graceful shutdown, degraded modes, and recovery objectives — producing a failure-mode table with a defined response for each. Use when designing a service, when adding a dependency, after an incident, or before a production readiness review.
when_to_use: Triggered by "reliability", "resilience", "what happens if X is down", "retry policy", "idempotency", "circuit breaker", "dead letter queue", "graceful shutdown", "disaster recovery", "RTO", "RPO", or a post-incident review.
argument-hint: [service or flow]
---

# Reliability review

Subject: `$ARGUMENTS`

## 1. Enumerate the failure modes

For every dependency and every step, ask what happens when it is:

- **Down** — connection refused, immediately and obviously
- **Slow** — the worst case, because it consumes your resources while failing
- **Wrong** — returns success with bad or partial data
- **Flapping** — intermittent, so retries sometimes work and mask the problem
- **Overloaded** — returns `429` or `503`, or just gets slower

Plus the failures that are not about dependencies:

- The process is killed mid-operation (deploy, OOM, node drain)
- Two replicas process the same work simultaneously
- A message is delivered twice, or out of order
- A poison message arrives that will never succeed
- The datastore is available but the write is rejected
- Clock skew between nodes

Build the table: failure · how it is detected · response · what the user sees.
**A row without a defined response is the finding** — that is the failure mode that
will take the service down.

## 2. Timeouts

Every outbound call has an explicit timeout. A call without one waits forever, and
for gRPC and many HTTP clients that is the default.

- Timeouts must be shorter as you go deeper, or the caller gives up while the callee
  is still working — wasted capacity on both sides.
- Propagate the remaining budget rather than starting a fresh timeout per hop. Three
  services each allowing 5 seconds is a 15-second worst case that nobody designed.
- The timeout must be shorter than the caller's patience and than any upstream proxy
  or ingress timeout, or the client sees a different error than you produce.

## 3. Retries — and the load they create

- Only retry what is safe and transient: `UNAVAILABLE`, `DEADLINE_EXCEEDED`, `503`,
  `429`, connection failures. Never retry validation or permission failures.
- Exponential backoff **with jitter**. Without jitter, every client retries in
  lockstep and the recovering service is knocked down again by its own clients.
- **A bounded budget**, both per-call attempts and as a fraction of total traffic. A
  service retrying three times turns a 20% failure rate into 60% extra load on
  something already struggling.
- Do not retry at multiple layers. Client, SDK, and service mesh each retrying three
  times is 27 attempts, and it is discovered during the outage it amplified.
- The final failure is logged once with the attempt count — see
  `${CLAUDE_PLUGIN_ROOT}/references/standards/logging.md`.

## 4. Idempotency

Retries and at-least-once delivery mean every operation runs more than once. For each
mutating operation, name the mechanism:

- An `Idempotency-Key` with a stored response —
  `${CLAUDE_PLUGIN_ROOT}/references/standards/api-rest.md`
- A conditional write or upsert on a natural key, with a unique index —
  `${CLAUDE_PLUGIN_ROOT}/references/stack/mongodb.md`
- Deduplication on `eventId` for consumers —
  `${CLAUDE_PLUGIN_ROOT}/references/standards/api-async-events.md`
- Naturally idempotent, with the reason stated

"It probably won't happen twice" is not a mechanism. **Exactly-once across a broker
and a database does not exist** without an outbox or a transactional sink.

## 5. Failed messages

Every consumer declares where permanently failed messages go, who owns that
destination, what alerts on it, and how it is drained. Distinguish permanent from
transient failure *before* spending the retry budget.

Note the difference that drives the design: in Kafka a poison message blocks its
partition; in RabbitMQ it does not. See
`${CLAUDE_PLUGIN_ROOT}/references/stack/kafka.md` and `rabbitmq.md`.

A DLQ with no alert and no drain procedure is data loss with extra steps.

## 6. Containing failure

- **Circuit breakers** on dependencies that can be slow. The point is to stop
  spending your own threads and connections on something that is not answering.
  Define the open threshold, the half-open probe, and the behaviour while open.
- **Bulkheads** — separate connection pools or thread pools per dependency, so one
  slow dependency cannot consume every worker.
- **Load shedding** — reject with `429` at a known limit rather than queueing without
  bound. Unbounded queueing converts a latency problem into an out-of-memory crash
  and loses the work anyway.
- **Degraded modes** — for each dependency, what still works when it is gone? A
  search outage that only disables search is much better than one that takes
  checkout with it. State this per dependency; it is usually the highest-value part
  of this review.

## 7. Lifecycle

- **Graceful shutdown**: stop accepting new work, finish in-flight work, commit,
  exit — all within `terminationGracePeriodSeconds`. For consumers, stop polling
  first. Getting this wrong is why deploys cause duplicate processing.
- **Probes**: liveness, readiness, and startup answer different questions. A liveness
  probe that checks a downstream dependency turns that dependency's outage into a
  fleet-wide restart loop. See `${CLAUDE_PLUGIN_ROOT}/references/stack/openshift.md`.
- **Rollback**: version N and N−1 coexist during a rolling update. A migration the
  previous version cannot read makes rollback impossible —
  `${CLAUDE_PLUGIN_ROOT}/references/standards/versioning.md`.

## 8. Recovery

- **RTO and RPO**, stated and achievable, not aspirational.
- Backups **verified by restoring**, on a schedule. An untested backup is a belief.
- The rebuild path for derived stores — an Elasticsearch index must be reconstructable
  from the source of truth, and that path must have been run at least once.
- The runbook covers the top three failure modes with steps someone has actually
  followed.

## 9. Decision checkpoints

Use `AskUserQuestion` for: shed versus queue versus degrade under overload; accepting
a single point of failure; RTO and RPO targets; whether a dependency is critical or
optional (which decides whether readiness fails when it is down); and adding an
outbox or a distributed lock.

## 10. Output

Write `docs/architecture/<slug>/reliability.md` or add the section to the design
document: the failure-mode table with a response for every row, the timeout and retry
policy per dependency, the idempotency mechanism per operation, the DLQ ownership,
the degraded-mode matrix, and RTO/RPO with how they were verified.

Report the rows that still have no defined response, ranked by likelihood times
impact. Those are the outages that are already scheduled; the date is just not known
yet.

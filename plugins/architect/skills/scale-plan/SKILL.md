---
name: scale-plan
description: Turn a traffic model into concrete capacity decisions — resource requests and limits, replica counts, Kafka partitions, Mongo working set and indexes, Elasticsearch shards, connection pools, and autoscaling triggers — and identify what breaks first under overload. Use when sizing a new service, when load is expected to grow, when something is slow under load, or before a production readiness review.
when_to_use: Triggered by "how many replicas", "how do we scale this", "sizing", "capacity planning", "how many partitions", "how many shards", "it falls over under load", "what happens at 10x traffic", or "set resource limits".
argument-hint: [service or flow]
---

# Scale plan

Subject: `$ARGUMENTS`

## 1. Build the traffic model

Nothing below can be decided without this, so do it first and write it down.

- **Steady-state rate** — requests, events, or records per second.
- **Peak rate and its shape** — a daily 3× spike is a different problem from a
  month-end 50× batch.
- **Growth** — the rate in twelve months, and where the number comes from.
- **Payload sizes** — average and worst case.
- **Read/write ratio** and the mix of expensive versus cheap operations.
- **Data volume growth** — total records and total bytes over time.

Where a number is unknown, state an assumption explicitly, mark it, and say how it
will be measured. **Do not invent numbers that look like measurements** — a
fabricated figure propagates into every sizing decision below and is indistinguishable
from a real one six months later.

## 2. Find the bottleneck before sizing anything

Work out which resource saturates first. It is rarely CPU. In this stack it is
usually one of:

- Mongo working set exceeding RAM — performance falls off a cliff rather than
  degrading
- Database connection pool exhaustion, especially once pods autoscale
- Kafka partition count capping consumer parallelism
- Elasticsearch heap pressure or rejected bulk writes
- A downstream synchronous dependency with a lower limit than yours
- A single hot partition or hot shard from a skewed key

Sizing everything else while the real bottleneck stays unaddressed is the most common
way capacity work fails.

## 3. Size each component

Apply the standards; do not size from defaults.

**Compute** — `${CLAUDE_PLUGIN_ROOT}/references/stack/openshift.md`. Requests from
observed usage. Always a memory limit; consider omitting the CPU limit to avoid
throttling that presents as unexplained latency. Replicas at or above the
availability floor.

**Kafka** — `${CLAUDE_PLUGIN_ROOT}/references/stack/kafka.md`. Partition count is a
ceiling on consumer parallelism and cannot be increased later without breaking
key-based ordering. Size for the twelve-month rate, not today's. Check the key for
skew — a hot partition cannot be scaled around.

**MongoDB** — `${CLAUDE_PLUGIN_ROOT}/references/stack/mongodb.md`. **The working set
(indexes plus hot documents) must fit in RAM** — this is the number to plan against.
Check for unbounded arrays and for queries with no supporting index.

**Elasticsearch** — `${CLAUDE_PLUGIN_ROOT}/references/stack/elasticsearch.md`. Target
10–50 GB per shard; too many shards is the more common error. Shard count is fixed at
creation.

**RabbitMQ** — `${CLAUDE_PLUGIN_ROOT}/references/stack/rabbitmq.md`. Prefetch, queue
bounds, and consumer count.

**Connection pools** — `pool size × max replicas` must stay under the datastore's
connection limit. Autoscaling multiplies pods, and the datastore limit is where that
gets discovered.

## 4. Autoscaling — and what it does to everything downstream

HPA on a metric reflecting the real bottleneck. CPU is the default and is frequently
wrong: a consumer bound by broker throughput does not respond to it. Queue depth or
consumer lag usually correlates better.

**Autoscaling a service autoscales load onto its dependencies.** `maxReplicas` is
bounded by what the datastore and downstream services can survive, not by what the
cluster can schedule. Kafka consumer replicas above the partition count simply idle.

## 5. What breaks first, and what happens then

State the failure sequence explicitly: at what multiple of expected peak does each
component saturate, in what order, and what does the user see at each stage.

Then decide the response for each: shed load with `429`, queue and process later,
degrade to a cheaper path, or fail fast. **Unbounded queueing is not a response** —
it converts a latency problem into an out-of-memory crash and loses the work anyway.
Cross-check the answers against `/architect:reliability-review`.

## 6. Decision checkpoints

Use `AskUserQuestion` for:

- Kafka partition count and the key (both effectively permanent)
- A Mongo shard key, or the decision to shard at all
- Elasticsearch shard count for a large index
- Whether to shed, queue, or degrade under overload
- Accepting a sizing based on an estimate rather than a load test

## 7. Output

Add a capacity section to the design document, or write
`docs/architecture/<slug>/scale-plan.md` for a standalone exercise. It contains: the
traffic model with each figure marked measured or estimated, the identified
bottleneck, the sizing decisions with their arithmetic, the autoscaling
configuration, and the overload sequence.

Record the permanent decisions — partition count, shard key, shard count — with
`/architect:adr`. These are the ones people most regret not being able to explain.

Report which numbers are measured and which are guesses, and what load test would
convert the guesses into measurements.

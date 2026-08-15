# Choosing between Kafka and RabbitMQ

The most frequently argued decision in this organization, and the most expensive to
get wrong, because both look like "a queue" from the calling code.

## The one-line rule

**Kafka is a durable, replayable, ordered log that many independent consumers read
at their own pace. RabbitMQ is a broker that routes individual messages to workers
and forgets them once they are handled.**

If the answer to "would a new consumer want to read everything that already
happened?" is yes, that is Kafka. If a message is a unit of work that one worker
does once and nobody will ever want again, that is RabbitMQ.

## Choose Kafka when

- **Multiple independent consumers** need the same stream, now or plausibly later.
  Adding a fifth consumer group to a Kafka topic costs nothing; adding a fifth
  consumer to a RabbitMQ queue means designing a fanout topology.
- **Replay matters.** A consumer bug means reprocessing from an offset rather than
  asking the producer to resend. This alone justifies Kafka for most event streams.
- **Ordering per key is required.** Kafka guarantees order within a partition;
  keying by entity ID gives per-entity ordering with parallelism across entities.
- **Volume is high and sustained** — tens of thousands of messages per second, or
  message retention measured in days.
- **The data is a fact, not a request.** "OrderPlaced" is a fact. "SendEmail" is a
  request.
- **Stream processing or joins** over the data are plausible.

## Choose RabbitMQ when

- **Work distribution.** A pool of workers each take the next task. Competing
  consumers on one queue is RabbitMQ's native shape and awkward in Kafka, where
  parallelism is bounded by partition count.
- **Per-message routing.** Header, topic-pattern, or priority routing to different
  handlers. Kafka has no routing — consumers filter, which means every consumer
  reads everything.
- **Per-message acknowledgement and redelivery.** A single failed message goes back
  on the queue or to a DLQ without stalling anything behind it. In Kafka, a poison
  message blocks its partition until the consumer decides to skip it.
- **Request/reply or RPC-ish** interactions with a correlation ID and reply queue.
- **Delayed or scheduled delivery** (delayed message exchange, TTL + dead-letter).
- **Low, bursty volume** where operating a partitioned log is overkill.

## The consequences of choosing wrong

**RabbitMQ where Kafka belonged.** Six months later a second team wants the same
events. You either build a second consumer and a fanout exchange, or you replay from
a database that was never designed to be an event log. The events that were consumed
before the second team existed are simply gone.

**Kafka where RabbitMQ belonged.** One malformed message stalls a partition. Your
parallelism is capped at the partition count you chose on day one and cannot be
lowered. You build retry topics, delay topics, and a DLQ topic to reimplement what
RabbitMQ does natively, and each of them needs its own consumer, monitoring, and
runbook.

**Both, for the same flow.** The most expensive outcome: two systems to operate, two
sets of failure modes, and no clear system of record for what happened.

## Decision checklist

Answer these before choosing. If the answers are mixed, the answer is usually Kafka
for the event stream plus a RabbitMQ queue for the work the events trigger — but
that is two components, and it needs an ADR.

1. How many consumers today? How many plausibly in two years?
2. Would a new consumer want history, or only messages from the moment it starts?
3. Is per-entity ordering required, or is order irrelevant?
4. Is a message a fact that happened, or an instruction to do something?
5. What happens to one poison message — must it be isolated, or can it stall a
   partition until someone intervenes?
6. Does any message need to be routed differently based on its content?
7. What is the sustained rate and the peak rate?
8. Does anything need delayed or scheduled delivery?

## Not an answer

- "We already have Kafka" is a real consideration but not a decision. Operational
  familiarity is worth something; it is not worth an unbounded workaround.
- "Kafka is faster" is usually irrelevant at organizational message volumes and is
  not a differentiator below a few thousand messages per second.
- "RabbitMQ is simpler" is true operationally and false at scale.

Whatever is chosen, record it with `/architect:adr` including which of the eight
questions above decided it. That question is what should be re-checked later.

See also `kafka.md`, `rabbitmq.md`, and
`../standards/api-async-events.md` for the contract rules that apply either way.

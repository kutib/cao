# Event and message contracts

An event schema is an API. It has consumers you cannot see, it cannot be changed
unilaterally, and unlike a REST call, the messages already published cannot be
recalled.

## Events versus commands

Be explicit about which you are publishing — the naming, the ownership, and the
coupling all differ.

| | Event | Command |
| --- | --- | --- |
| Means | Something happened | Please do something |
| Named | Past tense: `OrderPlaced` | Imperative: `SendInvoice` |
| Owner | The producer owns the fact | The consumer owns the capability |
| Consumers | Any number, unknown to producer | Usually exactly one |
| Coupling | Producer knows nothing of consumers | Producer knows the capability exists |
| Typical transport | Kafka | RabbitMQ |

A "command" fanned out to many consumers is usually a badly named event. An "event"
with exactly one consumer that must act on it is usually a command.

## The envelope

Every message carries the same envelope, regardless of transport:

| Field | Purpose |
| --- | --- |
| `eventId` | Unique per message. The consumer's idempotency key. |
| `eventType` | `orders.order.placed` — matches the topic or routing key |
| `schemaVersion` | Major.minor of the payload schema |
| `occurredAt` | When the fact happened, not when it was published |
| `producer` | Service name that emitted it |
| `correlationId` | Ties the message to the originating request |
| `causationId` | The message or request that caused this one |
| `traceparent` | W3C trace context, in transport headers — `../stack/opentelemetry.md` |

`occurredAt` and publish time are different, sometimes by hours after an outage.
Consumers that treat receipt time as event time compute wrong answers and nobody
notices for months.

## Payload design

- **Publish facts, not database rows.** A payload that mirrors an internal schema
  couples every consumer to your refactors.
- **Include what consumers need to act without calling back.** A thin event that
  forces every consumer to fetch the entity turns one publish into N reads and
  reintroduces the synchronous coupling the event was meant to remove.
- **But do not publish everything.** A payload carrying fields nobody consumes is a
  compatibility obligation with no benefit — and a data-exposure risk when it carries
  personal data into topics with long retention.
- No secrets, no credentials. Personal data only with a classification decision and a
  deletion story — see `data-classification.md`.

## Compatibility

Backward compatibility is the default: **a consumer written for v1 must keep working
when v2 messages arrive.**

Safe within a major version:
- Adding an optional field with a default
- Adding a new event type on a new topic
- Relaxing a constraint

Breaking, requiring a new major topic:
- Removing or renaming a field
- Changing a field's type or its meaning
- Making an optional field required
- Tightening a constraint
- Changing the key

The major version is part of the topic name (`orders.order.placed.v2`), so a
breaking change means publishing to both during a stated migration window, then
retiring v1 once consumers have moved. There is no way to migrate a topic in place.

**Changing the meaning of a field while keeping its type is the worst case**: nothing
fails, every consumer is silently wrong, and it is discovered in a reconciliation
weeks later. Treat it as a rename.

## Delivery semantics

State them per topic or queue, in the design:

- **At-least-once** is the realistic default for both Kafka and RabbitMQ. Every
  consumer must be idempotent — deduplicate on `eventId`, or use a conditional write
  keyed by a natural key. See `../stack/mongodb.md`.
- **Ordering** is per Kafka partition key, or not guaranteed at all in RabbitMQ with
  competing consumers. If a consumer depends on order, say so and key accordingly.
- **Exactly-once across a broker and a database does not exist** without an outbox on
  the producing side or a transactional sink on the consuming side. Anyone claiming
  otherwise has not yet had the incident.

## The outbox

When a state change and its event must both happen or neither, write the event to an
outbox collection in the same transaction as the state change, and publish from the
outbox. The alternative — write to the database, then publish — loses events on
crash between the two, and the reverse order publishes events for state changes that
never committed.

## Failure handling

Every consumer declares, before go-live:

- Its retry policy and budget.
- Where permanently failed messages go — DLQ topic or dead-letter queue.
- Who owns that DLQ, what alerts on it, and how it is drained.
- What a poison message does to throughput: in Kafka it blocks its partition, in
  RabbitMQ it does not. This difference drives the design.

## Documentation

Schemas live with the producing service and are published where
`../org-profile.md` says. AsyncAPI for the topic-level contract. The design document
names, for each topic: producer, known consumers, key, partition count or queue type,
delivery semantics, retention, and the DLQ path.

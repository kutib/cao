# MongoDB standards

Cluster topology and access model live in `../org-profile.md`.

## When MongoDB is the right store

- Document-shaped aggregates read and written as a unit.
- Flexible or evolving schema where the write side owns the shape.
- Primary-key and range access patterns known in advance.

**Not** for: full-text relevance search (that is Elasticsearch), analytics over
whole collections, or as a message queue. A collection polled for pending work is a
queue implemented badly — use RabbitMQ or Kafka.

## Schema follows queries

Design the access patterns first, then the document. Write the queries the
application will actually issue into the design document, then justify every index
by naming the query it serves.

**Embed** when the child data is read with the parent, is bounded, and is owned by
the parent. **Reference** when the child is large, unbounded, shared, or updated
independently.

**The unbounded array is the most common MongoDB design failure.** An array that
grows without limit — events, comments, log entries — eventually exceeds the 16 MB
document limit and degrades every read of that document long before it does. If a
list can grow forever, it belongs in its own collection.

## Indexes

- Every query in production is served by an index. Verify with `explain()`; a
  `COLLSCAN` on a growing collection is a future incident.
- **Compound index order: equality, then sort, then range.** Getting this order
  wrong produces an index the planner will not use for the sort.
- Indexes cost write throughput and memory. Ten indexes on a hot write collection is
  a design smell.
- **The working set — indexes plus frequently accessed documents — should fit in
  RAM.** When it stops fitting, performance does not degrade gracefully; it falls
  off a cliff. This is the number to plan capacity against.
- Partial and sparse indexes for fields present on a minority of documents.
- TTL indexes for data with a natural expiry — cheaper and more reliable than a
  cleanup job.
- Build indexes on large collections with awareness of the rolling-build procedure;
  a foreground build on a primary blocks writes.

## Writes and consistency

- **Write concern `majority`** for anything that must survive a primary failover.
  `w:1` acknowledges a write that a failover can lose. Choosing `w:1` is a decision
  that accepts data loss and needs to be stated.
- **Read concern and read preference** are explicit choices. Reading from secondaries
  scales reads but returns stale data; that is fine for some views and wrong for
  read-after-write flows.
- **Multi-document transactions exist but are a last resort.** They are expensive,
  hold locks, have a default 60-second limit, and their presence usually means the
  document boundaries are wrong. Redesign the aggregate first.
- Use conditional updates (`findOneAndUpdate` with a filter on the current state)
  rather than read-modify-write. Optimistic concurrency with a version field beats a
  transaction for most contention.

## Idempotency

Consumers of at-least-once messaging need idempotent writes. The pattern:
`updateOne({ _id: naturalKey }, { $setOnInsert: ... }, { upsert: true })` with a
unique index on the natural key. Catch the duplicate-key error and treat it as
success — that is the idempotency, not a failure.

## Sharding

Do not shard until a replica set genuinely cannot cope. When sharding is necessary:

- The shard key is effectively permanent — resharding is a project, not a config
  change.
- Avoid monotonically increasing keys (timestamps, ObjectIds) as shard keys; all
  writes land on one chunk.
- Avoid low-cardinality keys; they cap how far the cluster can spread.
- Hashed shard keys distribute well but destroy range-query locality. Know which one
  the workload needs.

## Multi-tenancy

Decide explicitly: shared collection with a tenant field, collection per tenant, or
database per tenant. Shared-with-tenant-field is the default and needs the tenant
field as the first element of every index and every query filter, enforced in one
place in the code rather than by convention.

## Operational

- Per-service credentials with least privilege. No shared application user across
  services, no root for application access.
- TLS in transit; encryption at rest per data classification.
- Connection pool sized deliberately: `pool_size × replica_count` must stay under
  the server's connection limit. Pods multiplying under autoscaling is how that limit
  is discovered in production.
- Backups are verified by restoring, on a schedule. An untested backup is a belief,
  not a control.
- Every migration is reversible or has a tested forward fix. Migrations run as a
  separate job, not on application startup, or N replicas race each other.

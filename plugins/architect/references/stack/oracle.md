# Oracle standards

Instance topology, service names, and connection limits live in `../org-profile.md`.

Oracle and MongoDB are both first-class in this platform. Neither is the default —
see `datastore-choice.md`, and record the choice in an ADR.

## When Oracle is the right store

- Data with real relational structure, queried across entities in ways that are not
  known up front.
- Multi-entity transactions that must be atomic, with genuine ACID guarantees.
- Strong constraints enforced by the database: foreign keys, uniqueness, check
  constraints. When correctness matters more than write throughput, the database
  enforcing invariants beats every application-level attempt.
- Reporting and analytical queries over normalized data.
- An existing Oracle system of record that new work must integrate with.

**Not** for: document-shaped aggregates that are always read as a unit, schemaless or
rapidly evolving data, full-text relevance search, or as a queue. A table polled for
pending rows is a queue implemented badly — use RabbitMQ or Kafka.

## Connections — the failure that will find you

**This is the single most common way an Oracle-backed service fails on OpenShift.**

Oracle instances have a hard `processes` / `sessions` limit, shared across every
client. Your budget is:

```
pool_max_size × max_replicas ≤ your service's allocated share of the instance
```

Autoscaling multiplies pods, and every pod brings a full pool. A service that runs
fine at 3 replicas exhausts the instance at 30 and takes down **every other service
on that instance**, not just itself.

Rules:

- `maxReplicas` is bounded by the connection budget, not by what the cluster can
  schedule. State the arithmetic in the design — see `../../skills/scale-plan`.
- Pools are small. A pool of 10 per pod is almost always too large; connection count
  is not throughput, and an idle pooled connection still consumes a server process.
- Set a connection acquisition timeout. Without one, pool exhaustion presents as
  requests hanging forever rather than as a fast, diagnosable failure.
- Validate connections on borrow, or a network blip leaves the pool full of dead
  handles.
- Set both a connect timeout and a statement timeout. An external database is a
  dependency like any other — see `../standards/…` and the reliability review.

## Queries

**Bind variables, always.** Never build SQL by concatenating values. Two reasons, and
both matter:

1. Injection — see `../standards/security-baseline.md`.
2. **Hard parsing.** Oracle caches execution plans keyed on statement text. Literal
   values produce a distinct statement per value, so every query is a hard parse.
   This floods the shared pool, burns CPU, and degrades the whole instance — again,
   for every service on it, not just yours.

Other rules:

- Every query in production has a supporting index and a checked execution plan. Read
  the plan; do not assume. A full table scan on a growing table is a scheduled
  incident.
- **Index order: equality columns, then range, then the columns you sort on.**
- Avoid functions on indexed columns in a `WHERE` clause — it disables the index
  unless a matching function-based index exists.
- **N+1 is the dominant application-level performance bug** with any ORM. Fetch what
  you need in one statement; verify by counting statements in a test, not by reading
  the code.
- Bound every result set. `SELECT` with no limit is an unbounded input.
- Beware implicit type conversion between the application and the column type; it
  silently disables index use.

## Schema and transactions

- Model from the access patterns and the invariants. Let the database enforce what it
  can enforce better than you can: foreign keys, unique constraints, check
  constraints, not-null.
- Sequences for surrogate keys, with a sensible cache size. A sequence with `NOCACHE`
  under load serializes inserts.
- Keep transactions short. A transaction held open across a network call to another
  service holds locks for the duration of that call's worst case.
- Default isolation is read-committed; understand what that means for read-modify-write
  and use `SELECT ... FOR UPDATE` or optimistic concurrency with a version column
  rather than hoping.
- Optimistic concurrency (a version column) beats pessimistic locking for most
  contention, and does not hold a lock across think time.
- Partition large tables by the dimension you actually prune on — usually a date.
  Partitioning that does not match the query predicates costs maintenance and buys
  nothing.

## Idempotency

Consumers of at-least-once messaging need idempotent writes. The Oracle pattern is a
unique constraint on the natural key plus an insert that tolerates the duplicate-key
violation, or a `MERGE` keyed on it. Catching the constraint violation and treating it
as success **is** the idempotency — see `../standards/api-async-events.md`.

## Migrations

- Versioned and tool-managed (Liquibase or Flyway per `../org-profile.md`). No manual
  DDL against an environment.
- Run as a separate job, never on application startup — N replicas racing each other
  through DDL is a corrupted schema.
- **Every migration must be compatible with the previous application version**,
  because during a rolling update both versions are live and a rollback must remain
  possible. Expand and contract: add the new column nullable, deploy code writing both,
  backfill, then drop the old column in a **later** release. See
  `../standards/versioning.md`.
- DDL on a large table is not free. Adding a nullable column is cheap; adding a
  constraint validates every existing row and can lock the table. Know which you are
  doing before you run it in production.
- Every migration is reversible, or has a tested forward fix.

## Operational

- Per-service schema and per-service credentials with least privilege. No shared
  application account across services, no DBA-level account for application access.
- TLS in transit; encryption at rest per `../standards/data-classification.md`.
- The database is outside the cluster: it is a dependency with a NetworkPolicy egress
  rule, a timeout, a retry policy, and a defined behaviour when it is unreachable.
- Backups are verified by restoring, on a schedule.
- Watch: active sessions against the limit, pool wait time, hard parse rate, top SQL
  by elapsed time, blocking locks, and tablespace growth.
- Integration tests run against a real Oracle instance or container, not against an
  in-memory substitute pretending to be one — see
  `../standards/testing-and-coverage.md`. Dialect differences are exactly where the
  bugs live.

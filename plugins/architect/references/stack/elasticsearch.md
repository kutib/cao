# Elasticsearch standards

Cluster topology lives in `../org-profile.md`.

## What Elasticsearch is for

Search and analytics: relevance ranking, full-text, aggregations, and querying by
fields you did not plan for. It is a **derived** store.

**Elasticsearch is not the system of record.** It has no transactions, its refresh
is near-real-time rather than immediate, and reindexing is normal maintenance. If
losing the whole cluster and rebuilding it from another store is not an option, the
architecture is wrong. The source of truth is MongoDB, or the Kafka topic that fed
it, and there is a documented, tested rebuild path.

## Mappings

- **Explicit mappings. Disable dynamic mapping** (`dynamic: strict` or `false`) on
  any index taking external data. Dynamic mapping plus an unexpected field is how a
  cluster acquires a mapping explosion and stops accepting writes.
- `keyword` for exact match, filtering, aggregation and sorting. `text` for
  relevance search. Fields needing both get a multi-field.
- Mappings are immutable for existing fields. Changing a type means a new index plus
  a reindex behind an alias — plan for it rather than discovering it.
- Do not index what you never query. Every indexed field costs space and write
  throughput; set `index: false` on stored-but-unsearched fields.

## Indices and aliases

- **Always read and write through an alias, never a concrete index name.** This is
  what makes a zero-downtime reindex possible. Retrofitting aliases during an
  incident is not fun.
- Time-series data uses data streams or rollover with ILM: hot, then warm, then
  delete. Set the retention explicitly; "keep everything" is a decision to run out
  of disk at an unpredictable date.
- Naming: `<domain>-<entity>-<version>` for the concrete index,
  `<domain>-<entity>` for the alias.

## Shards

The most common sizing mistake is too many shards, not too few.

- Target **10–50 GB per shard**. Under a few GB, a shard is pure overhead.
- Start with one primary shard per index unless the data clearly exceeds 50 GB.
  Small indices do not need five shards because that used to be the default.
- Shard count is fixed at creation; changing it means reindex or split/shrink.
- One replica minimum in production, for availability and read capacity.
- Every shard costs heap on every node. A cluster with thousands of tiny shards is
  slow at everything, including recovery.

## Queries

- **Filter context for anything not contributing to relevance.** Filters are cached
  and skip scoring; putting date ranges and term filters in `must` instead of
  `filter` throws away that cache.
- Avoid leading wildcards, script queries in hot paths, and deep pagination. Use
  `search_after` with a tiebreaker rather than `from`/`size` beyond a few thousand
  documents.
- Aggregations on high-cardinality fields are memory-hungry. Bound them, and know
  the cardinality before shipping.
- Set an explicit query timeout and handle partial results — `timed_out: true` with
  partial shard results looks like success to naive client code.

## Indexing pipeline

The path from source of truth to index is part of the design, not an afterthought:

- **Source:** the Kafka topic or MongoDB change stream that feeds it.
- **Bulk writes**, sized in bytes rather than document count. Handle per-item
  failures in the bulk response — a 200 response can contain failed items, and
  ignoring them is silent data loss.
- **Backpressure:** what happens when the cluster rejects writes (HTTP 429). Retry
  with backoff, and shed or buffer rather than dropping.
- **Reindex path:** documented and tested before go-live. Write to a new index,
  verify counts, flip the alias, delete the old one.
- **Lag:** the time between a change in the source of truth and its visibility in
  search is an SLI. Measure it and set a target.

## Operational

- Per-service credentials scoped to the specific indices and actions.
- TLS in transit; field-level security or a separate index for restricted data — see
  `../standards/data-classification.md`.
- JVM heap at or below 31 GB, and no more than half of node RAM; the rest is the
  filesystem cache that makes search fast.
- Snapshots to the configured repository on a schedule, with restore tested.
- Watch: cluster status, unassigned shards, heap pressure, rejected bulk requests,
  and indexing lag. Yellow status on a single-replica index in production is a
  standing risk, not a temporary state.

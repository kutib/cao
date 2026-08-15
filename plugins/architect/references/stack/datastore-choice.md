# Choosing between Oracle, MongoDB, and Elasticsearch

Oracle and MongoDB are both first-class in this platform. **Neither is the default.**
Every new service justifies its store and records the choice in an ADR.

Elasticsearch is not in that contest: it is a derived store, never a system of record.

## The one-line rule

**Oracle when the data has relational structure and invariants the database should
enforce. MongoDB when the data is a document read and written as a unit. Elasticsearch
when you need relevance, full text, or aggregation over data that lives somewhere
else.**

## Choose Oracle when

- Entities relate to each other and are queried across those relationships in ways not
  fully known up front. Joins are the point.
- A single business operation must atomically touch several entities.
- Invariants matter enough that the database should enforce them: foreign keys,
  uniqueness, check constraints. An invariant enforced in application code across
  three services is not enforced.
- Reporting or analytical queries run over normalized data.
- It integrates with an existing Oracle system of record, and splitting the data would
  create a distributed consistency problem where none exists today.

## Choose MongoDB when

- The natural unit of work is a document read and written whole — an order with its
  lines, a profile with its preferences.
- The schema varies by record or evolves quickly, and the writing service owns the
  shape.
- Access is by key and by known query patterns, planned in advance.
- Write throughput and horizontal scale matter more than cross-entity transactions.

## Elasticsearch is a derived store

Use it for search, relevance, and aggregation. It is fed from Oracle, MongoDB, or a
Kafka topic, and it must be rebuildable from that source. If losing the cluster and
reindexing is not an option, the architecture is wrong. See `elasticsearch.md`.

## The consequences of choosing wrong

**MongoDB where Oracle belonged.** Multi-document transactions appear, then spread.
Referential integrity becomes application code that is subtly wrong in three places.
Reports need joins the database cannot do, so they move into application memory. The
first reconciliation finds orphaned records nobody can explain.

**Oracle where MongoDB belonged.** A document is shredded across eight tables and
reassembled on every read. Every schema change is a migration. The service's release
cadence is now governed by DDL, and the join count grows with each feature.

**Elasticsearch as the system of record.** Discovered during the first reindex, when
it turns out nothing else has the data. Near-real-time refresh means a write is not
immediately readable, and something downstream has been silently depending on that.

**Both Oracle and MongoDB in one service.** Sometimes correct, usually a sign the
service does two jobs — check `../standards/separation-of-concerns.md`. It always means
two consistency models, two failure modes, two backup and restore procedures, and an
unanswerable question about which one is authoritative when they disagree.

## Decision checklist

Answer these before choosing. Take the answers to `/architect:tech-select`, which will
ask you to confirm and then record the decision.

1. What is the unit of work — a single document, or several related entities?
2. Does any operation need to atomically change more than one entity?
3. Which invariants must be guaranteed, and what breaks if one is violated once?
4. Are the query patterns known now, or will people ask new questions of this data?
5. Does anything need to join this data with data in another table or collection?
6. How fast does the schema change, and who owns its shape?
7. What is the write rate, and what is the total volume in two years?
8. Does anything need full-text or relevance search over it? (That is an
   Elasticsearch index fed from the answer above, not a reason to change the answer.)
9. Is there an existing system of record for this data? If yes, the burden of proof is
   on introducing a second one.

## Not an answer

- "The team knows Oracle better" is real and worth weighing, but it is a cost, not a
  requirement. Say it out loud in the ADR rather than dressing it as a technical
  argument.
- "MongoDB is faster" is meaningless without naming the operation. Oracle is faster at
  joins; Mongo is faster at fetching a whole document.
- "We can always migrate later" is true and expensive. Migrations between these two
  are projects, not refactors. Weight the decision accordingly.

Record the outcome with `/architect:adr`, naming the deciding question from the list
above. That question is what should be re-checked when the service changes shape.

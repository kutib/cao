# Data classification

Classification determines the controls. Classify the data **before** designing where
it is stored, what is logged, and how long it is retained — retrofitting is a
migration project across every store the data reached.

## Levels

| Level | Examples | If disclosed |
| --- | --- | --- |
| **Public** | Published documentation, public catalogue data | No harm |
| **Internal** | Service topology, non-sensitive operational data, aggregate metrics | Embarrassing, exploitable for reconnaissance |
| **Confidential** | Personal data, customer records, commercial terms, credentials | Regulatory exposure, real harm to individuals |
| **Restricted** | Payment data, health data, government identifiers, authentication secrets | Severe; likely reportable, likely contractual breach |

When in doubt, classify up and ask the data owner. Under-classifying is discovered by
an auditor or an incident.

## Controls by level

| Control | Internal | Confidential | Restricted |
| --- | --- | --- | --- |
| TLS in transit | Yes | Yes | Yes |
| Encryption at rest | Recommended | Yes | Yes |
| Access logged | No | Yes | Yes, with review |
| Field-level access control | No | Where practical | Yes |
| Permitted in application logs | Yes | No — identifiers only | No |
| Permitted in span attributes | Yes | Identifiers only | No |
| Permitted as a metric label | Yes, if low cardinality | No | No |
| Permitted in a long-retention Kafka topic | Yes | Only with a deletion plan | Avoid entirely |
| Permitted in a prompt, embedding, or vector index | Yes | Only with a deletion plan | Avoid entirely |
| Retention | By need | Stated and enforced | Minimum viable, enforced |
| Deletion on request | N/A | Required, provable | Required, provable |

## The propagation problem

Classified data does not stay where it was put. Before designing a flow, trace every
destination:

- The primary store (Oracle or MongoDB)
- Any derived store (Elasticsearch indices — including old indices behind aliases)
- Every Kafka topic it passes through, **for the full retention period**
- Dead-letter queues and topics, which are frequently forgotten and often retained
  longest
- Application logs and the log backend
- Traces and span attributes
- Backups and snapshots
- Non-production environments, if production data is ever copied down

### AI destinations — new, and nobody tracks them

If a language model is anywhere in the path, the data also reaches:

- **Prompts and completions**, retained wherever the model gateway retains them — see
  `../org-profile.md`. Decide this rather than inheriting it.
- **Embeddings and the vector or search index** built from the data. An embedding is
  derived from the content and is a copy for classification purposes.
- **Agent traces and tool-call arguments**, which record what was retrieved and passed
  around.
- **Any MCP tool result** that returned the data to a model.

Each has its own retention and its own deletion problem, and an index built from a
source you later must delete from is a deletion obligation nobody planned. The usual
right answer is the same as for Kafka: **pass identifiers, not personal data**, and
keep the data in the one place that can actually delete it. See
`ai-engineering.md`.

**Kafka is where deletion promises go to die.** A "delete this customer's data"
request cannot be satisfied by deleting a Mongo document if the same data sits in a
topic with 30-day retention and in three consumers' derived stores. Decide up front:
keep personal data out of long-retention topics, use short retention with compaction
and tombstones, or store a reference and keep the data in one place that can actually
delete it.

The last option is usually right: **publish identifiers, not personal data.**

## Personal data specifics

- Collect the minimum. A field nobody uses is pure liability.
- Pseudonymize where the use case allows — an internal ID instead of an email address
  in every downstream system.
- Deletion must be provable end to end, including derived stores and backups. Say
  explicitly how backups are handled, since they usually cannot be selectively
  edited.
- Non-production environments do not receive production personal data without
  masking. "Just this once, to debug" is how it ends up permanently in staging.

## In the design document

Every design states, for each significant dataset: its classification, its owner, its
stores, its retention in each, and its deletion path. A design that cannot answer
"how do we delete this everywhere?" is not finished.

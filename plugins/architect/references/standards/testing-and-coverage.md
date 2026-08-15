# Testing and the Sonar quality gate

SonarQube gates CI. Server, quality gate name, and thresholds are in
`../org-profile.md`.

## What the gate measures

The gate is evaluated **on new code** — the lines changed in this branch — not on the
whole repository. This matters: it means a legacy service with 20% coverage is not
blocked forever, and it means a small change to a bad file is still held to the
standard.

Typical conditions: coverage on new code, duplicated lines on new code, no new issues
above a severity, and all new security hotspots reviewed.

## Coverage is a floor, not a goal

**A covered line is not a tested behaviour.** Coverage measures which lines executed
during the test run. It cannot tell you whether anything was asserted, whether the
assertion was meaningful, or whether the important case was the one you skipped.

The failure modes, in order of how often they appear in review:

- Tests that execute code and assert nothing, or assert only that no exception was
  thrown.
- Tests asserting on mocks rather than on outcomes — proving the code called what you
  told it to call, which is a restatement of the implementation.
- Every getter tested, no error path tested.
- The happy path covered, the failure branches — the ones that run during an incident
  — untested.

**When coverage is short of the gate, the question is which behaviour is untested, not
which lines are uncovered.** Those usually have the same answer, and when they do not,
the lines are the wrong thing to chase.

## What to test at each level

**Unit** — business rules, calculations, state transitions, edge cases and error
paths. Fast, no infrastructure. This is where the density belongs.

**Integration** — the code that talks to something real. Against a real Oracle,
MongoDB, Elasticsearch, Kafka, or RabbitMQ in a container, not an in-memory
substitute pretending to be one. **Dialect and driver differences are precisely where
the bugs live**: the index that is not used, the compound-index ordering, the
transaction semantics, the offset commit. A test against a fake proves your fake
works.

Specifically worth an integration test, because a unit test cannot catch it:

- A query is served by the index you think it is
- A migration applies and rolls back
- A consumer is idempotent under redelivery
- Authorization rejects a valid token from another tenant
- Serialization round-trips exactly

**Contract** — the service matches its published spec, generated from the spec rather
than from the implementation. See `api-contract-first.md`.

**End-to-end** — a few, covering the critical user journeys. They are slow and
fragile; they are not where coverage comes from.

## Exclusions

Configure them deliberately. Legitimate exclusions:

- **Generated code** — OpenAPI and gRPC stubs, generated clients, MCP tool bindings.
  Not excluding these makes the gate unwinnable and rewards writing tests for
  generated getters. See `api-contract-first.md`.
- Framework boilerplate with no logic: configuration classes, module wiring, plain
  DTOs with no behaviour.
- Migration scripts, which are verified by applying them rather than by unit tests.

**Not** legitimate, and recognizable in review:

- Excluding a package because its coverage is low.
- Excluding the error handling, the retry logic, or the authorization code — the
  hardest things to test are the things most worth testing.
- Broad wildcards that quietly grow to cover new code.
- Marking real code as generated.

Every exclusion is reviewable and has a stated reason. Exclusions belong in the
committed Sonar configuration, never passed as ad-hoc analysis parameters.

## Working with the gate honestly

When the gate fails on coverage:

1. Find the untested **behaviour**, not the uncovered line.
2. If the uncovered code has no behaviour worth asserting — a trivial delegation, a
   generated accessor — that is a signal it may belong in an exclusion category, or
   that the code should not exist.
3. If it is genuinely hard to test, that is usually a design finding: I/O tangled with
   logic, a dependency that cannot be substituted, a method doing four things. Fix the
   seam and the test becomes easy. See `separation-of-concerns.md`.
4. Never add assertion-free tests to move the number. It passes the gate, hides the
   risk, and makes the metric useless for everyone afterwards.

Suppressing an issue or lowering the gate is a decision, and a decision goes in an
ADR with the reason and the person who accepted it.

## Flaky tests

A test that fails intermittently is worse than a missing test: it trains the team to
re-run the build until it passes, which is also how a real failure gets ignored.

Quarantine it immediately, with an owner and a date. A quarantined test is a bug, not
a state of being. The usual causes are shared state between tests, dependence on
wall-clock time, unawaited asynchrony, and test-order dependence.

## Security hotspots

Sonar raises hotspots for review, not as defects. Each is reviewed by a human and
marked safe with a reason, or fixed. Bulk-marking hotspots safe to clear the gate
defeats the mechanism entirely — and the categories it raises (injection, weak crypto,
permissive CORS, hardcoded credentials) map directly onto
`security-baseline.md`.

---
name: test-strategy
description: Design a component's test strategy and make the SonarQube quality gate winnable honestly — what to test at each level, which exclusions are legitimate, and how to close a coverage gap by testing the untested behaviour rather than gaming the metric. Use when planning tests, when the Sonar gate fails, or when deciding what to exclude from coverage.
when_to_use: Triggered by "test strategy", "Sonar", "SonarQube", "quality gate", "coverage", "coverage is failing", "what should we test", "how do we test this", "flaky test", "test exclusions", or "security hotspot".
paths:
  - "**/sonar-project.properties"
argument-hint: [component, or the failing gate]
---

# Test strategy

Subject: `$ARGUMENTS`

Standard: `${CLAUDE_PLUGIN_ROOT}/references/standards/testing-and-coverage.md`.
Sonar server, gate name, and thresholds:
`${CLAUDE_PLUGIN_ROOT}/references/org-profile.md`.

## If the gate is currently failing, start here

Read the actual gate result before proposing anything — which condition failed, on
which files, and by how much. Then work the real question:

**Which behaviour is untested?** Not which lines are uncovered. They usually have the
same answer, and when they do not, the lines are the wrong thing to chase.

For each uncovered area, one of these is true:

1. **A real behaviour has no test.** Write it. This is the common case and the whole
   point of the gate.
2. **The code has no behaviour worth asserting** — a generated accessor, a trivial
   delegation. Check whether it belongs in a legitimate exclusion category, or whether
   it should exist at all.
3. **It is genuinely hard to test.** That is a design finding, not a testing problem:
   I/O tangled with logic, a dependency that cannot be substituted, a method doing four
   things. Fix the seam and the test becomes easy — see
   `${CLAUDE_PLUGIN_ROOT}/references/standards/separation-of-concerns.md`.

**Never propose assertion-free tests to move the number.** They pass the gate, hide the
risk, and make the metric useless for everyone afterwards. If asked to do this
directly, say plainly what it costs and offer the real fix.

## Design the strategy

**Unit** — business rules, calculations, state transitions, and the error paths. Fast,
no infrastructure. The density belongs here.

**Integration** — against a real Oracle, MongoDB, Elasticsearch, Kafka, or RabbitMQ in
a container, never an in-memory substitute pretending to be one. Name the specific
failure each test catches. The ones that only an integration test can catch:

- The query is served by the index you think it is
- A migration applies **and** rolls back
- A consumer is idempotent under redelivery
- Authorization rejects a valid token from another tenant
- Serialization round-trips exactly

**Contract** — the service matches its published spec, generated from the spec rather
than from the implementation. See
`${CLAUDE_PLUGIN_ROOT}/references/standards/api-contract-first.md`. A test written
against the implementation agrees with whatever the code does, including the drift it
was meant to catch.

**End-to-end** — a few, for critical journeys. Slow and fragile; not where coverage
comes from.

## Exclusions

Legitimate: generated code (OpenAPI and gRPC stubs, generated clients, MCP tool
bindings — excluding these is required, not optional, or the gate is unwinnable),
framework boilerplate with no logic, and migration scripts verified by applying them.

Not legitimate, and recognizable in review: excluding a package because its coverage is
low; excluding error handling, retry logic, or authorization code; broad wildcards that
quietly grow; marking real code as generated.

Every exclusion is in the committed Sonar configuration with a stated reason — never
passed as an ad-hoc analysis parameter.

## Decision checkpoints

Use `AskUserQuestion` for:

- Adding an exclusion that is not clearly in the legitimate list
- Suppressing an issue or lowering the gate — a decision that needs an ADR naming who
  accepted it
- Accepting a known coverage gap for a release, with an owner and a date

Do not make these choices silently. They are exactly the decisions someone will ask
about later.

## Security hotspots

Sonar raises hotspots for human review, not as defects. Each is reviewed and marked
safe with a reason, or fixed. **Bulk-marking hotspots safe to clear the gate defeats
the mechanism** — and the categories it raises map directly onto
`${CLAUDE_PLUGIN_ROOT}/references/standards/security-baseline.md`.

## Flaky tests

A test that fails intermittently is worse than a missing test: it trains the team to
re-run the build, which is how a real failure gets ignored. Quarantine immediately with
an owner and a date. Usual causes: shared state between tests, wall-clock dependence,
unawaited asynchrony, test-order dependence.

## Output

Add a test-strategy section to the detailed design, or write
`docs/architecture/<slug>/testing.md`: what each level covers and which failure modes
it catches, the integration tests and what they run against, the exclusions with
reasons, and any accepted gap with its owner.

Report: the behaviours that were untested, what you added or recommend adding, any
exclusion you propose and why it is legitimate, and any design problem the difficulty
of testing revealed.

# ADR {NNNN}: {Title — the decision, stated as a claim}

- **Status:** Proposed | Accepted | Superseded by ADR-NNNN | Deprecated
- **Date:** {YYYY-MM-DD}
- **Deciders:** {names — the humans who chose, not the tool that drafted}
- **Domain:** {high-level architecture | detailed architecture | api | tech stack | security | scale | separation of concerns | observability | metrics | reliability}

## Context

What situation forces a decision now? State the problem, the constraints that are
genuinely fixed, and the requirements that drive the choice. Include numbers where
they exist — expected volume, latency budget, team size, deadline.

Do not describe the solution here.

## Options considered

### Option A: {name}

- **How it works:** one paragraph.
- **Costs:** operational burden, complexity, licensing, learning curve.
- **Risks:** what could go wrong, and how badly.

### Option B: {name}

Same shape. Include the option that was rejected — an ADR listing only the chosen
option is a press release, not a decision record.

## Decision

**We will {do X}.**

Why this option beat the others, in terms of the context above. Name the deciding
factor explicitly: the one thing that, if it changed, would flip this decision.

## Consequences

**Accepted costs.** What is now harder, slower, or more expensive.

**New obligations.** What the team must now do forever: an index to maintain, a
consumer group to watch, a schema registry entry, an extra dashboard.

**Blast radius.** What breaks if this turns out to be wrong, and how hard it is to
reverse. Rate reversibility: easy (config change) | moderate (a sprint) | hard
(migration project).

## Revisit when

The conditions that should make someone re-open this decision. For example:
"volume exceeds 5k msg/s", "a second consumer needs the same stream", "the vendor
drops on-premise support".

## References

Links to the design document, the ticket, the benchmark, the prior ADR this
supersedes.

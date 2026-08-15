---
name: separation-of-concerns
description: Decide where a boundary belongs — new service versus new module, how layers depend on each other, and where coupling has crept in — using an explicit cost test rather than taste. Use when asked whether to split or extract a service, when a module has grown unclear, when two components keep changing together, or when reviewing dependency direction.
when_to_use: Triggered by "should this be its own service", "split the monolith", "extract a service", "where should this code live", "these two things are too coupled", "circular dependency", "bounded context", or "is this the right layer".
argument-hint: [component or decision under discussion]
---

# Separation of concerns

Subject: `$ARGUMENTS`

Standard: `${CLAUDE_PLUGIN_ROOT}/references/standards/separation-of-concerns.md`.
Read it — the cost test and the coupling catalogue below are compressed from it.

## 1. Establish what is actually being asked

Three different questions hide behind "how should we separate this":

- **Should this be a separate deployable?** (service versus module)
- **Where should this code live inside the service?** (layering and packaging)
- **Why do these two things keep changing together?** (existing coupling)

Identify which one, because the analysis differs completely.

## 2. Service versus module

**The default answer is no new service.** Apply the cost test explicitly rather than
by feel.

A new service is justified when at least one is true, concretely and now:

- Its scaling profile genuinely differs — different resource shape, different load
  curve, and the current coupling is causing real waste.
- Its release cadence is genuinely blocked by the current coupling — name the
  release that was delayed.
- Its availability requirement differs — one part must survive the other's failure.
- It sits behind a different security, tenancy, or data-residency boundary.
- A different team owns it, with separate on-call.

It is **not** justified by: the file is long, the concept feels distinct, the diagram
looks nicer, or a general preference for smaller services.

Then state the cost out loud, because it is always paid and rarely counted: a network
hop with its own timeouts and partial failures, a versioned contract, either a shared
datastore (coupling) or a split one (distributed consistency), separate deployment,
observability, alerting and on-call, and any transaction that spanned the boundary
becoming a distributed problem.

**A module is the reversible choice.** Extracting a well-separated module later is a
normal refactor. Merging two services back together almost never happens, so the
asymmetry favours waiting.

## 3. Layering and dependency direction

Dependencies point inward, toward business rules, away from I/O:

```
inbound adapters → application → domain ← outbound adapters
```

Check, concretely, in the code:

1. Does any domain type import a framework, driver, or transport type? Persistence
   annotations on domain objects are the usual violation.
2. Does the application layer define the interfaces it needs, with adapters
   implementing them — or does it import the driver directly?
3. Could the domain logic be exercised with no database, broker, or HTTP server
   running? If not, the direction is inverted somewhere.
4. Are there cycles between modules, packages, or services? A cycle between two
   services means they are one service that cannot deploy independently.

## 4. Find the coupling

Look for these specifically, in the repository rather than in the abstract:

- **Shared datastore between services** — the schema has become an undocumented
  contract that neither team can change.
- **A "common" library containing domain logic or entities** — every service now
  upgrades in lockstep. A distributed monolith.
- **Synchronous chains three or more deep** — availability multiplies, latency adds.
- **The same business rule implemented twice** — they will diverge, and a customer
  will find it first.
- **Data owned by two components** — decide which one owns writes.
- **Temporal coupling** — A must deploy before B. Legitimate sometimes; must be
  written down when it exists.

For each one found, say what it costs today and what removing it would cost. Not
every coupling is worth removing; the ones worth removing should be obvious once both
numbers are stated.

## 5. Decision checkpoint

Use `AskUserQuestion` for: new service versus module, splitting a shared datastore,
breaking up a shared library, and introducing an anti-corruption layer against a
system you do not control.

Present the cost test result and a recommendation. When the honest answer is "leave
it as one service for now", say that — recommending a split because it sounds more
architectural is how organizations acquire distributed monoliths.

## 6. Output

For a structural decision: record it with `/architect:adr`, including the specific
justification that cleared the cost test and the conditions that would reopen it
(for example, "revisit when the ingest path needs to scale separately from the API").

For a review finding: report the coupling, its cost today, and the cheapest change
that reduces it. Rank by cost, not by how offensive the coupling looks.

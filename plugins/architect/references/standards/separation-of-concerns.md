# Boundaries, layering, and coupling

## The default answer is "no new service"

A new service buys independent deployment, independent scaling, and a hard team
boundary. It costs a network hop with its own failure modes, a contract to version,
its own datastore or a shared one with all the coupling that implies, separate
observability, separate on-call, and distributed transactions where a function call
used to be.

**Justified by:** a genuinely different scaling profile, a different availability
requirement, a different release cadence that is blocked today, a different security
or data-residency boundary, or an actual team boundary with separate ownership.

**Not justified by:** the code file is long, the domain concept feels distinct, the
diagram looks tidier, or a preference for microservices. A module inside an existing
service gets most of the boundary benefits at none of the operational cost, and can
be extracted later — extracting a well-separated module is a normal refactor;
merging two services back together rarely happens.

**The strongest signal that a split is right:** two parts of the system change for
different reasons, at different times, driven by different people. **The strongest
signal it is wrong:** every feature needs a coordinated change to both sides.

## Dependency direction

Dependencies point inward, toward the code that expresses business rules and away
from I/O.

```
inbound adapters  →  application  →  domain  ←  outbound adapters
(HTTP, consumers)    (use cases)     (rules)    (Mongo, ES, Kafka clients)
```

- The domain layer imports nothing from frameworks, drivers, or transport.
- The application layer orchestrates and depends on domain types and on *interfaces*
  it defines for its outbound needs.
- Adapters implement those interfaces. The database driver depends on the
  application, never the reverse.

**The test:** could this domain code be exercised with no database, no broker, and no
HTTP server running? If not, the direction has been inverted somewhere, and the usual
culprit is a persistence annotation or a driver type on a domain object.

**No cycles**, at any level — between modules, packages, or services. A cycle between
two services means they are one service that cannot be deployed independently, which
was the entire reason for splitting them.

## Coupling to watch for

- **Shared datastore between services.** The most common accidental coupling: the
  schema becomes an undocumented contract, and neither team can change it. If two
  services genuinely need the same data, one owns it and the other reads it through
  an API or a published event stream.
- **Shared "common" library** containing domain logic. A shared library of genuinely
  generic utilities is fine. One containing entities or business rules means every
  service upgrades in lockstep — distributed monolith, worst of both worlds.
- **Chatty synchronous chains.** A → B → C → D within one request means the
  availability is the product of four services and the latency is their sum. Three
  hops is a smell; four is a design error.
- **Temporal coupling.** Service A must be deployed before B, or a flow breaks.
  Legitimate occasionally; must be written down when it exists.
- **Semantic coupling.** Two services with their own copy of the same business rule.
  They will diverge, and the divergence will be discovered by a customer.

## Anti-corruption layers

When integrating with a system whose model you do not control — a legacy system, a
vendor, another domain's API — translate at the boundary. The foreign model does not
leak past the adapter.

Without this, the vendor's field names, their enum values, and their peculiar notion
of what a customer is spread through your codebase, and you inherit their next
breaking change everywhere at once.

The cost is a mapping layer and a set of translation tests. It is almost always worth
it, and it is the thing most often skipped under deadline pressure.

## Cohesion inside a service

- Organize by feature or domain concept, not by technical layer. `orders/` containing
  its handler, use case, domain, and repository beats four top-level directories
  named `controllers/`, `services/`, `models/`, `repositories/` — the latter means
  every change touches four distant places.
- A module has one reason to change. If its description needs "and", look harder.
- Keep the public surface of a module small and explicit. Everything exported is a
  contract with the rest of the codebase.

## Applying this in review

Ask, in this order:

1. What is this component's single responsibility, in one sentence without "and"?
2. What does it depend on, and does anything point the wrong way?
3. If this changes, what else must change with it?
4. Could it be tested without infrastructure?
5. Is any data owned by two things?
6. Is any business rule implemented twice?

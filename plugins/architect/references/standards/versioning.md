# Versioning and compatibility

The rule underneath everything here: **you cannot change a contract, you can only
publish a new one and retire the old one.** Every rule below follows from that.

## What is a contract

Anything another team observes: REST endpoints and their payloads, gRPC services,
event schemas and topic names, shared database schemas, and the semantics of any
field in any of them. Internal implementation is not a contract, and should be
arranged so that most changes are internal.

## Semantic versioning of contracts

- **Major** — a breaking change. New endpoint path, new topic name, new proto
  package. The old one keeps running.
- **Minor** — additive and backwards compatible. New optional field, new endpoint,
  new event type.
- **Patch** — documentation and clarification only, with no behaviour change.

REST carries the major version in the path: `/v1/orders`. Events carry it in the
topic name: `orders.order.placed.v1`. gRPC carries it in the package:
`orders.v1.OrderService`. Header-based and content-negotiated versioning are not
used — they are invisible in logs, dashboards, and routing rules.

## Additive is safe, everything else is not

**Safe:**
- Adding an optional request field with a server-side default
- Adding a response field (clients must ignore unknown fields — say so in the contract)
- Adding an endpoint, event type, or RPC
- Adding an enum value **only if** clients were told to tolerate unknown values from
  day one; otherwise it is breaking
- Relaxing a validation rule

**Breaking:**
- Removing or renaming anything
- Changing a type, a format, or a unit
- Making an optional field required, or adding a required field
- Tightening validation
- Changing a default
- Changing the meaning of a field while leaving its shape alone — the most dangerous
  of all, because nothing fails and everything is quietly wrong
- Changing an error code, a status code, or the conditions that produce them
- Changing a partition key or an ordering guarantee

## Deprecation

A major version is not retired when the new one ships. The sequence:

1. Publish the new version. Both run.
2. Announce the deprecation with a date, to consumers **identified by name**. "We
   announced it in the channel" is not consumer identification.
3. Instrument the old version so you can see who is still calling it. Usage data
   ends the argument about whether anyone still depends on it.
4. Mark it deprecated in the contract — `deprecated: true` in OpenAPI, `Deprecation`
   and `Sunset` response headers.
5. Retire it when usage is zero, or when the announced date passes and the remaining
   consumers have accepted the break in writing.

The minimum window is set in `../org-profile.md`. Retiring a version with live
traffic is an outage you caused on purpose.

## Rollback compatibility

Every deploy must be rollback-safe, which means **version N and version N−1 have to
coexist**, because during a rolling update they do.

- A schema migration that the previous version cannot read makes rollback impossible.
  Use expand-and-contract: add the new shape, deploy code that writes both and reads
  either, backfill, then remove the old shape in a **later** release.
- A consumer that cannot handle the old message format cannot be rolled back after
  the producer has been.
- Producer and consumer deploy order must be stated in the design when it matters.
  Usually: consumers understand the new format first, producers emit it second.

## Compatibility testing

- Contract tests run in CI against the published contract, not against the current
  implementation. A test that reads the implementation's own schema proves nothing.
- Event schemas are checked for backward compatibility on every change, mechanically.
- Keep a recorded set of real historical payloads and assert that current consumer
  code still handles them. This catches the "changed the meaning" class of break that
  schema checking cannot see.

## Client obligations

Publish these with every contract, because compatibility is a two-sided property:

- Ignore unknown fields.
- Tolerate unknown enum values with a defined fallback.
- Do not depend on field order, on JSON key ordering, or on the absence of a field.
- Do not parse human-readable messages.
- Treat any `5xx` or timeout as retryable, and anything else as not.

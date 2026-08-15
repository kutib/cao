---
name: api-design
description: Design or change a contract other teams depend on — REST endpoints, gRPC services, or event schemas — contract-first from an OpenAPI/proto/AsyncAPI specification, applying the org standards for resources, status codes, errors, pagination, idempotency, compatibility, deprecation, and the edge gateway boundary. Use whenever an OpenAPI document, .proto file, AsyncAPI spec, or event payload is created or modified, and before any change that could break a consumer.
when_to_use: Triggered by "design an API", "add an endpoint", "change this payload", "new event schema", "is this a breaking change", "how should we version this", "generate the client", "codegen", or by editing any openapi/asyncapi/.proto file.
paths:
  - "**/openapi*.y*ml"
  - "**/openapi*.json"
  - "**/swagger*.y*ml"
  - "**/swagger*.json"
  - "**/asyncapi*.y*ml"
  - "**/*.proto"
argument-hint: [api or endpoint name]
---

# API design

Subject: `$ARGUMENTS`

## 0. The spec is the build's source of truth

**APIs are built from their specification.** The OpenAPI document — or `.proto`, or
AsyncAPI — is written first, reviewed with the consumer while changing it is still
free, and the implementation is generated from it. Read
`${CLAUDE_PLUGIN_ROOT}/references/standards/api-contract-first.md` before designing.

Two consequences that hold for every task below:

- **Generated code is never hand-edited**, never carries business logic, and is
  excluded from coverage — see
  `${CLAUDE_PLUGIN_ROOT}/references/standards/testing-and-coverage.md`. Map generated
  models to domain types at the boundary.
- **CI must enforce four things**, or this is documentation rather than a contract:
  lint the spec, detect breaking changes against the published version, prove the
  running service conforms to it, and regenerate-and-diff if generated code is
  committed. If any is missing, that is a finding to report.

If the API already exists without a spec, retrofitting is normal — generate one,
**verify it against real behaviour**, then let it lead. A spec asserted to be accurate
and never checked is worse than none, because consumers trust it.

## 1. Identify what kind of contract this is

| Kind | Standard |
| --- | --- |
| HTTP API called by another team or a client | `${CLAUDE_PLUGIN_ROOT}/references/standards/api-rest.md` |
| Internal service-to-service RPC | `${CLAUDE_PLUGIN_ROOT}/references/standards/api-grpc.md` |
| Event or message published to a broker | `${CLAUDE_PLUGIN_ROOT}/references/standards/api-async-events.md` |

Error semantics apply to all three:
`${CLAUDE_PLUGIN_ROOT}/references/standards/errors.md`.
Compatibility rules apply to all three:
`${CLAUDE_PLUGIN_ROOT}/references/standards/versioning.md`.

Read the relevant standard before writing the contract. Do not reconstruct it from
memory — the details that get skipped are exactly the ones that cause breakage.

## 2. If this is a change to an existing contract

Answer this first, before anything else: **is it breaking?**

Consult the safe/breaking lists in `versioning.md`. The ones most often
misjudged:

- Adding a required field — breaking.
- Adding an enum value — breaking unless consumers were told from day one to
  tolerate unknown values.
- Tightening validation — breaking.
- Changing what a field *means* while its type stays the same — breaking, and the
  worst kind, because nothing fails and every consumer is quietly wrong.
- Changing an error code or the condition that produces it — breaking.

If it is breaking, stop and use `AskUserQuestion`: publish a new major version
alongside the old one (the default), or coordinate a break with named consumers.
"Consumers were notified in a channel" does not count as coordination. Record the
outcome with `/architect:adr`.

Then identify the actual consumers by name. If nobody knows who consumes it, that is
the first finding to report.

## 3. Design the contract

Work from the consumer's use case backwards. The questions that matter:

- What does the caller have, and what do they need? The contract should not require
  them to make three calls to do one thing.
- What is the resource model, and does it match how consumers think about the domain
  rather than how the database stores it?
- Which operations are idempotent, and which need an `Idempotency-Key`?
- What are the failure cases, and which are retryable? Every one gets a stable code.
- What bounds apply — page size, batch size, payload size, rate limit? An unbounded
  parameter is a denial-of-service vector against your own datastore.
- Is every filterable and sortable field backed by an index? A contract that promises
  a query the datastore cannot serve is a performance incident with a schedule.

For events, additionally: is this a fact or a command; what is the key and therefore
the ordering guarantee; what is the retention; who are the consumers; where do failed
messages go.

For anything reachable from outside, settle the **gateway boundary** —
`${CLAUDE_PLUGIN_ROOT}/references/stack/nginx-gateway.md`. The nginx edge handles TLS,
routing, rate limits, request size limits, and early rejection of anonymous traffic.
It never handles per-resource authorization, business validation, or idempotency, and
**the service must be safe when called directly**. State the size and rate limits per
route and the timeout chain from client through gateway to service.

## 4. Decision checkpoints

Use `AskUserQuestion` for:

- Breaking versus versioning an existing contract
- Synchronous API versus published event for a new integration
- REST versus gRPC where both would work
- Embedding related data in a response versus requiring a second call
- Exposing a field carrying personal data — check
  `${CLAUDE_PLUGIN_ROOT}/references/standards/data-classification.md` first

## 5. Write it down

The contract is a file in the repository — OpenAPI, `.proto`, or AsyncAPI — written
**before** the implementation and published where `${CLAUDE_PLUGIN_ROOT}/references/org-profile.md`
says. Include:

- Every status code or error code the operation can produce, with its condition.
- The compatibility promise and the deprecation policy.
- Rate limits and expected latency per operation.
- Examples for the non-obvious cases, not just the happy path.

## 6. Report

Tell the developer: what the contract is, whether anything is breaking and for whom,
the bounds and idempotency decisions, which consumers need to be told, and **which of
the four CI checks in step 0 are missing**. If a breaking change was chosen, confirm the
ADR exists and names the deprecation date.

# Contract-first API development

**APIs are built from their specification.** The OpenAPI document is not documentation
written after the fact — it is the source of truth the build depends on. The same
applies to `.proto` for gRPC and AsyncAPI for events.

This is a build rule, not a preference: if the implementation can drift from the spec
without CI noticing, the spec is documentation and consumers will be misled by it.

## The sequence

1. **Write the spec.** Endpoints, schemas, status codes, error shapes, examples.
   Apply `api-rest.md`.
2. **Review the spec with the consumer** — before implementation, while changing it is
   still free. This is the entire point of contract-first, and skipping it wastes the
   effort.
3. **Generate** server interfaces and client SDKs from it.
4. **Implement** against the generated interfaces.
5. **Prove conformance in CI.**
6. **Publish** the spec where consumers find it, per `../org-profile.md`.

## Generated code

- **Generated code is never hand-edited.** An edit is silently lost on the next
  generation, and CI cannot tell you which behaviour is real.
- Generate into a separate, clearly marked directory or module — it must be obvious at
  a glance which code is generated.
- Generation runs in the build, not once on a developer's machine. Whether the output
  is committed is a per-repository decision; if it is committed, CI regenerates and
  fails on a diff.
- **Business logic never goes in a generated type.** Map generated request and
  response models to domain types at the boundary. Letting generated models reach the
  domain layer inverts the dependency direction and couples the domain to the wire
  format — see `separation-of-concerns.md`.
- **Generated code is excluded from coverage.** This is not optional: including it
  makes the Sonar gate unwinnable and pushes people toward meaningless tests over
  generated getters. Configure the exclusion deliberately and see
  `testing-and-coverage.md` for the line between a legitimate exclusion and gaming the
  gate.

## CI must enforce all four

A contract-first process with none of these is contract-shaped documentation.

1. **Lint the spec.** Spectral or equivalent, against a shared ruleset encoding
   `api-rest.md`: naming, required error responses, documented status codes,
   pagination on collections, bounded parameters.
2. **Detect breaking changes.** Diff the spec against the published version
   (`oasdiff` or equivalent) and fail on a break. Consult
   `versioning.md` for what counts — the ones tooling catches are only the structural
   half; a changed field *meaning* passes every diff tool and breaks every consumer.
3. **Prove conformance.** The running service must match the spec. Contract tests
   generated from the spec, or request/response validation against it in integration
   tests. **A test written against the implementation proves nothing** — it will agree
   with whatever the code does, including the drift you are trying to catch.
4. **Regenerate and diff**, if generated code is committed.

## Where specs live

- In the producing service's repository, versioned with the code that implements them.
  A spec in a separate repository drifts, because nothing forces the two to change
  together.
- Published to the org location on merge, so consumers always read the deployed
  version rather than a branch.
- One spec per service. Splitting one API across several documents makes
  breaking-change detection and client generation harder for no gain.

## When the API already exists

Retrofitting is normal and worth doing:

1. Generate a spec from the current behaviour, by hand or from the implementation.
2. **Verify it against reality** with real traffic or contract tests. A generated spec
   documents what the code does, including its bugs and its accidents.
3. Fix the spec where the behaviour was wrong and the fix is non-breaking; record the
   behaviour where it is breaking, and version it out later.
4. From that point, the spec leads and the CI checks apply.

Do not skip step 2. A spec asserted to be accurate, and not checked, is worse than no
spec — consumers will trust it.

## gRPC and events

The same rule, different artifact. `.proto` files are the source of truth for gRPC —
see `api-grpc.md`; AsyncAPI or the registered schema is the source of truth for
events — see `api-async-events.md`. Both are generated from, linted, and checked for
compatibility in CI exactly as above.

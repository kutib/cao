# Production readiness review: {service name}

- **Date:** {YYYY-MM-DD}
- **Service owner / on-call team:** {name}
- **Target go-live:** {date}
- **Verdict:** Go | Go with conditions | No-go

Each item is **met**, **not met**, or **not applicable** — with a one-line
justification. "Not applicable" without a reason counts as "not met".

## Design and decisions

- [ ] HLD exists and is approved
- [ ] Detailed design exists for non-trivial components
- [ ] Every architectural fork has an ADR in `docs/adr/`
- [ ] No component outside the platform set without an approving ADR

## Contracts

- [ ] API contract published (OpenAPI / proto / AsyncAPI) and versioned
- [ ] **Implementation generated from the spec; generated code not hand-edited**
- [ ] **CI lints the spec, detects breaking changes, and proves conformance**
- [ ] Backwards-compatibility policy stated; consumers identified by name
- [ ] Error responses follow the org error standard
- [ ] Event schemas registered; compatibility mode set

## Tests and quality gate

- [ ] SonarQube quality gate passing on new code
- [ ] Every coverage exclusion has a stated reason and is in committed configuration
- [ ] Integration tests run against real Oracle / Mongo / Elasticsearch / broker
- [ ] Security hotspots individually reviewed, not bulk-cleared
- [ ] No quarantined flaky tests without an owner and a date

## Security

- [ ] Threat model completed; no open high-impact threats
- [ ] Authentication via Red Hat SSO on every entry point, including internal ones
- [ ] **Token validation checks signature, issuer, audience, and expiry**
- [ ] **Service verified safe when called directly, bypassing the gateway**
- [ ] Authorization rules tested, including the negative cases
- [ ] No secrets in git, images, or environment defaults
- [ ] TLS in transit; encryption at rest where classification requires it
- [ ] NetworkPolicy applied, default deny
- [ ] Container runs non-root, read-only root filesystem, no privilege escalation
- [ ] Image scanned; no unaddressed critical vulnerabilities

## Scale and capacity

- [ ] Expected load documented, with the basis for the estimate
- [ ] Load tested at expected peak and at 2× peak
- [ ] Resource requests and limits set from measurement, not guesswork
- [ ] Horizontal scaling verified; no hidden singleton state
- [ ] Datastore sized: Mongo working set, ES shard count, Kafka partitions
- [ ] **Connection budget checked: pool size × maxReplicas within the Oracle allocation**
- [ ] Gateway route limits set: request size, rate limit, timeout chain
- [ ] What breaks first under overload is known and documented

## Reliability

- [ ] Every outbound call has a timeout
- [ ] Retries use backoff with jitter and a budget; retry storms considered
- [ ] Non-idempotent operations protected by idempotency keys or conditional writes
- [ ] DLQ or equivalent exists for every consumer, with a documented drain procedure
- [ ] Graceful shutdown drains in-flight work within the termination grace period
- [ ] Degraded mode defined: what still works when each dependency is down
- [ ] Backup and restore tested by actually restoring, not by reading the runbook
- [ ] RTO and RPO stated and achievable

## Observability

- [ ] OpenTelemetry traces cover every entry point and outbound call
- [ ] Trace context propagates across HTTP and message boundaries
- [ ] Logs are structured, correlated to trace IDs, and free of secrets and PII
- [ ] Resource attributes follow the org convention (`service.name`, version, namespace)
- [ ] Sampling configured deliberately, with errors always sampled

## Metrics and alerting

- [ ] SLIs defined for availability and latency; SLO targets agreed with the consumer
- [ ] Error budget and its policy agreed
- [ ] Dashboard exists showing RED metrics and dependency health
- [ ] Alerts fire on user-visible symptoms, not on internal causes
- [ ] Every alert has a runbook link and a tested response
- [ ] No alert fires more than once a week in steady state

## AI features (if a model is anywhere in the path)

- [ ] Eval set exists, built from real cases, and passes at the agreed threshold
- [ ] Evals run in CI and block a regressing release
- [ ] Eval set includes injection and authorization-bypass cases
- [ ] Tool authority is the minimum for the task; read and write tools separated
- [ ] Tools authorize as the calling user, not as a service account
- [ ] Human confirmation before every irreversible action
- [ ] Agent loops bounded: steps, wall-clock, and spend
- [ ] Retrieval authorized at query time, not by filtering results afterwards
- [ ] Injection posture stated: what untrusted text reaches the model, and the blast
      radius if injection succeeds
- [ ] Model output validated or encoded before reaching any sink that trusts it
- [ ] No secrets in prompts, tool descriptions, or tool results
- [ ] Every `stop_reason` handled, including refusal and truncation
- [ ] Degraded path defined for a slow, unavailable, or refusing model
- [ ] Cost ceilings set and monitored
- [ ] Kill switch tested — the feature can be disabled without a deploy

## Operations

- [ ] Liveness, readiness, and startup probes configured and distinct
- [ ] PodDisruptionBudget set; rolling update verified with no dropped requests
- [ ] Runbook covers: deploy, roll back, common failures, escalation
- [ ] On-call team has been trained and has accepted the pager
- [ ] Rollback tested from the actual deployed version
- [ ] Data migration, if any, is reversible or has a tested forward fix

## Conditions and follow-ups

For a "go with conditions" verdict: list each condition, its owner, and its date.

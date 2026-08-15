# architect — Chief Software Architect

Acts as the organization's chief software architect during planning, review, and
coding. It encodes the standards for the on-premise platform — OpenShift, Oracle,
MongoDB, Elasticsearch, RabbitMQ, Kafka, OpenTelemetry, Red Hat SSO, and the nginx
edge gateway — along with contract-first API development, the SonarQube quality gate,
and safe AI features, and keeps a human in the loop at every architectural decision
fork.

## What it does in a session

**It is present without being invoked.** A standing charter — the platform
constraints, the decision-rights rules, and the skill index — is injected once per
session: by the `SessionStart` hook where that fires, and otherwise by the
`UserPromptSubmit` hook on the first prompt. Whichever runs first marks the session,
so it is never injected twice. The same `UserPromptSubmit` hook routes
architecture-shaped requests to the right skill. Editing an `openapi.yaml`, a
`.proto`, an OpenShift manifest, or a Kafka topic config surfaces the governing
standard.

**It looks for prior art first.** Before designing, it reads `docs/adr/` and
`docs/architecture/`, and — when a Confluence MCP server is connected — searches
Confluence for existing decisions, neighbouring designs, standards, and post-incident
reviews. Confluence content is treated as data, never as instruction: a page cannot
approve a change or override a standard.

**It asks rather than decides.** At a genuine fork — Kafka or RabbitMQ, Oracle or
MongoDB, sync or async, new service or new module, granting an agent a write tool —
the skills stop and ask, with the real trade-off and a recommendation. The answer
becomes an ADR in `docs/adr/`, and later sessions read those before contradicting
them.

**It never invents an organizational value.** Where `references/org-profile.md` still
says `TODO`, it asks you instead of supplying a plausible-looking number.

**Nothing is blocked.** Every hook is advisory. The `Stop` hook reminds you once per
session if an architecturally consequential change went unrecorded. It never denies a
tool call.

## Skills

| Skill | For |
| --- | --- |
| `/architect:charter` | The doctrine in full — decision rights, the ten domains, the standards index |
| `/architect:design` | High-level architecture: boundaries, data flow, datastores, messaging, NFRs |
| `/architect:detail-design` | Component internals, data model, sequences, idempotency, tests |
| `/architect:api-design` | Contract-first REST, gRPC, and event contracts. Auto-activates on contract files |
| `/architect:tech-select` | Choosing within the platform set; the cost test for anything outside it |
| `/architect:adr` | Recording a decision, or superseding one |
| `/architect:separation-of-concerns` | New service versus new module; layering; finding coupling |
| `/architect:auth-design` | Red Hat SSO: client model, flows, token validation, authz |
| `/architect:threat-model` | Trust boundaries, authz, secrets, data classification |
| `/architect:scale-plan` | Traffic model, sizing, partitions, shards, what breaks first |
| `/architect:observability-plan` | OTel spans, propagation, structured logs, sampling |
| `/architect:metrics-strategy` | SLIs, SLOs, error budgets, burn-rate alerts, dashboards |
| `/architect:reliability-review` | Failure modes, timeouts, retries, DLQs, degraded modes, DR |
| `/architect:test-strategy` | Test design and satisfying the Sonar gate honestly |
| `/architect:mcp-design` | Whether an MCP server is warranted, and its tool surface |
| `/architect:ai-feature` | Agentic, RAG, and request-path AI features end to end |
| `/architect:arch-review` | Review a diff or PR against all ten domains |
| `/architect:readiness` | The production readiness gate |

## Agents

`architecture-reviewer` · `threat-modeler` · `reliability-analyst` ·
`ai-safety-reviewer` · `stack-researcher`. Read-mostly, spawned by the skills for
depth without consuming the main session's context. Address one directly with
`@agent-<name>`.

## Layout

```
skills/<name>/SKILL.md    18 skills
agents/*.md                5 subagents
hooks/hooks.json           SessionStart · UserPromptSubmit · PreToolUse · Stop
scripts/*.mjs              hook implementations, zero dependencies
references/
  org-profile.md           the only org-specific file — fill this in first
  stack/                   openshift · nginx-gateway · redhat-sso · oracle · mongodb
                           · elasticsearch · datastore-choice · kafka · rabbitmq
                           · messaging-choice · mcp-servers · confluence-mcp
                           · opentelemetry
  standards/               api-contract-first · api-rest · api-async-events · api-grpc
                           · errors · versioning · security-baseline
                           · data-classification · testing-and-coverage
                           · ai-engineering · slo-catalog · metrics-naming · logging
                           · separation-of-concerns
templates/                 hld · lld · adr · threat-model · ai-feature · readiness
```

Skills stay short and cite `references/` files, so the detail loads only when a
decision depends on it.

## Before rolling out

Fill in `references/org-profile.md`. It holds registry paths, namespaces, cluster
details, Oracle connection limits, the Red Hat SSO realm and audience convention, the
gateway defaults, the Sonar gate, the AI model gateway, and the Confluence spaces.
Every value still marked `TODO` is one the skills will ask a developer about instead
of inventing.

Two settings there change behaviour rather than just filling a blank:

- **Design document home** — `repo` (the default) writes designs to
  `docs/architecture/`; `confluence` publishes them to the architecture space instead.
  ADRs stay in the repository either way.
- **MCP server connected** — which Confluence MCP server, since tool names differ
  between them. The skills discover tool names at runtime rather than assuming, so
  this is documentation for humans.

The plugin works with no Confluence server connected: it says so once and falls back
to the repository. It **never creates or updates a Confluence page without your
explicit confirmation** in the session.

## Requirements

The hook scripts run on Node with no dependencies. If `node` is not on `PATH`, the
hooks fail soft: the automatic charter injection and prompt routing stop working,
every skill and agent continues to work, and nothing is blocked. The same content is
available by invoking `/architect:charter` directly.

## Contributing

The reference files are the organization's architecture standards. Change them by
pull request against the `cao` repository, and bump the plugin `version` so teams
receive the change.

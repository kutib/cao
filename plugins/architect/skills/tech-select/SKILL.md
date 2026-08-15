---
name: tech-select
description: Choose a technology for a specific need, working within the fixed on-premise platform set (OpenShift, MongoDB, Elasticsearch, RabbitMQ, Kafka, OpenTelemetry) and applying a real cost test to anything outside it. Ends in a human decision and an ADR. Use when choosing between Kafka and RabbitMQ, Mongo and Elasticsearch, or when someone proposes adding a new component, library, or datastore.
when_to_use: Triggered by "which database should we use", "Kafka or RabbitMQ", "should we add Redis", "what should we use for X", "can we introduce <technology>", or any proposal to add a component to the stack.
argument-hint: [the need, e.g. "cache for session data"]
---

# Technology selection

Need: `$ARGUMENTS`

If the need was not stated, ask what problem the technology is meant to solve —
**the problem, not the candidate**. "We need Redis" is a proposed answer; the
question underneath it might be caching, locking, rate limiting, or session storage,
and those have different answers.

## 1. State the requirement in measurable terms

Before comparing anything, pin down:

- What operation, at what rate, with what latency budget?
- What are the durability and consistency requirements? What is the cost of losing
  one item? Of losing all of it?
- What access patterns — key lookup, range, full text, aggregation, streaming?
- How much data, and how does it grow?
- Who else needs this data, now and plausibly later?

A requirement that cannot be stated this way is not ready for a technology choice.

## 1a. Check whether this was already decided

Search `docs/adr/` and — when a Confluence MCP server is connected — Confluence, for a
prior decision on this need or a neighbouring one. A technology chosen elsewhere in the
organization is a strong argument, and re-deciding it in isolation is how a platform
acquires three message brokers. See
`${CLAUDE_PLUGIN_ROOT}/references/stack/confluence-mcp.md`.

## 2. Try the platform set first

The platform is fixed on purpose:
`${CLAUDE_PLUGIN_ROOT}/references/org-profile.md`.

| Need | Platform answer | Reference |
| --- | --- | --- |
| Relational data, transactions, invariants | Oracle | `references/stack/oracle.md` |
| Document store, system of record | MongoDB | `references/stack/mongodb.md` |
| **Oracle vs MongoDB vs Elasticsearch** | the nine-question checklist — **neither Oracle nor Mongo is the default** | `references/stack/datastore-choice.md` |
| Search, relevance, aggregation | Elasticsearch (derived, never source of truth) | `references/stack/elasticsearch.md` |
| Event stream, replay, many consumers | Kafka | `references/stack/kafka.md` |
| Work distribution, routing, RPC | RabbitMQ | `references/stack/rabbitmq.md` |
| Kafka vs RabbitMQ | the eight-question checklist | `references/stack/messaging-choice.md` |
| Compute, scaling, scheduling | OpenShift | `references/stack/openshift.md` |
| Authentication | Red Hat SSO | `references/stack/redhat-sso.md` |
| External API entry | nginx edge gateway | `references/stack/nginx-gateway.md` |
| Traces, metrics, logs | OpenTelemetry | `references/stack/opentelemetry.md` |
| Exposing a capability to an AI agent | MCP server — but read "when not to" first | `references/stack/mcp-servers.md` |

Read the relevant reference before comparing. Most selection arguments are settled
by a constraint already written down there.

## 3. The cost test for anything outside the set

A new component must clear both bars:

1. **The platform set genuinely cannot do this** — not "does it less elegantly",
   but cannot. Say specifically what fails.
2. **The workaround costs more than the component's lifetime operational cost.**
   That cost is not the licence. It is: patching, upgrades, backups, restore
   testing, monitoring, alerting, capacity planning, an on-call rotation that
   understands it, security review, and the day it fails at 3am and two people in
   the organization know how it works.

If either bar is not cleared, the answer is the boring platform option, and that is
a good outcome.

## 4. Compare honestly

For each candidate that survives step 3:

| Candidate | How it meets the requirement | Operational cost on-premise | Failure modes | Reversibility |
| --- | --- | --- | --- | --- |

Include the **do-nothing option** and the **use what we already have, imperfectly**
option. They are frequently correct and frequently unexamined.

State what you do not know. "No one here has run this in production" is a material
risk, and hiding it is how a proof of concept becomes a dependency.

## 5. Decide — with the human

Use `AskUserQuestion`. Present the candidates, recommend one, and state the deciding
factor and what would flip it. Do not present a menu without a recommendation; that
is abdication, not consultation.

If the human picks a different option than recommended, that is their call. Record
their reasoning in the ADR rather than yours.

## 6. Record it

Invoke `/architect:adr` with the decision. The ADR must include:

- The requirement in measurable terms from step 1.
- The rejected candidates and why.
- For a component outside the platform set: how it cleared both bars in step 3, and
  who accepted the operational cost — by name.
- The conditions that should reopen the decision.

An addition to the platform set is not complete until the platform team has accepted
the operational burden. If they have not, the ADR status is `Proposed`, not
`Accepted`, and the plugin should say so plainly.

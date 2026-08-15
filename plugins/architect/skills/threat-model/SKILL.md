---
name: threat-model
description: Threat model a system or change — trust boundaries, entry points, STRIDE threats with mitigations, secrets handling, the authorization rule written out, data classification, and network posture — producing a document with named owners for anything left open. Use before a new service ships, when adding an entry point or integration, when handling personal or regulated data, or when reviewing anything auth-related.
when_to_use: Triggered by "threat model", "security review", "is this secure", "we're adding authentication", "handling PII", "who can call this", "secrets management", or before a production readiness review.
argument-hint: [system or component]
---

# Threat model

Subject: `$ARGUMENTS`

Baseline: `${CLAUDE_PLUGIN_ROOT}/references/standards/security-baseline.md`
Classification: `${CLAUDE_PLUGIN_ROOT}/references/standards/data-classification.md`
Template: `${CLAUDE_PLUGIN_ROOT}/templates/threat-model.md`

## 1. Classify the data first

Before modelling anything, classify what flows through the system, and trace **every**
destination it reaches: primary store, derived indices, Kafka topics for their full
retention, dead-letter destinations, logs, span attributes, backups, and any
non-production environment that receives a copy.

This step decides most of the controls, and doing it late means retrofitting across
every store the data already reached.

If the design cannot answer "how do we delete this everywhere?", that is a finding,
not a detail.

## 2. Map trust boundaries and entry points

**Entry points** — every way in, including the ones people forget: message consumers,
scheduled jobs, admin and management interfaces, debug and metrics endpoints, and the
container itself.

**Boundaries** — every place control changes hands. For each: what authenticates,
what authorizes, and what protects the transport. A boundary with no authentication
is a finding, and "it is only reachable inside the cluster" is an assumption that
holds until one pod is compromised.

## 3. Enumerate threats

STRIDE per entry point and per boundary. Keep only threats that are real for this
system — a table of generic threats is worse than nothing because it looks like work
was done.

For each: likelihood, impact, mitigation, and a status of mitigated (say how),
accepted (say who accepted it, by name), transferred (to which control), or open
(with an owner and a date).

**Look hardest at these, because they are the ones that actually happen here:**

1. **Object-level authorization.** Can an authenticated user read or modify another
   user's or tenant's data by changing an identifier? Route-level checks do not catch
   this. Verify the tenant filter is enforced in one place, not by convention in every
   query.
2. **Token validation.** Are signature, issuer, audience, *and* expiry all checked?
   Signature alone accepts tokens minted for a different service.
3. **Injection into datastore queries.** Client input reaching a Mongo filter or an
   Elasticsearch query unparameterized — operator injection through a JSON body is
   easy to miss.
4. **Unbounded input.** Payload size, array length, page size, batch size, query
   complexity. Each is a denial-of-service vector.
5. **Secrets in reachable places.** Repository, image layers, environment defaults,
   log lines, error messages, span attributes, metric labels.
6. **Sensitive data leaving through telemetry.** The most common accidental
   disclosure path, because nobody reviews what a log line contains.

## 4. Write the authorization rule out

In words: who may do what to which resource, and where that is enforced. Include the
negative cases — what a valid but unprivileged token cannot do.

An authorization model that exists only as scattered checks in handlers cannot be
reviewed and cannot be tested. Writing it out is usually where the gaps surface.

## 5. Decision checkpoints

Use `AskUserQuestion` when the model reaches:

- Accepting a residual risk — a human must accept it, by name, and it is recorded
- Storing confidential or restricted data in a new location
- Putting personal data into a topic with long retention
- An exception to the security baseline
- A choice between authorization models (role-based, attribute-based, ownership)

## 6. Output

Write to `docs/architecture/<system-slug>/threat-model.md`. Record accepted risks and
baseline exceptions with `/architect:adr` — an accepted risk that lives only in a
document nobody re-reads is an unowned risk.

Report: the classification, the number of threats by status, every open threat with
its owner and date, and specifically whether the seven checks in
`security-baseline.md` all pass.

## What not to do

- Do not produce a generic STRIDE table that would apply to any system. It is
  reassuring and worthless.
- Do not mark something mitigated because a control exists somewhere. Say where, and
  say how it was verified.
- Do not accept a risk on the developer's behalf. Acceptance is a named human
  decision.

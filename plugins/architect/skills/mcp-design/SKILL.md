---
name: mcp-design
description: Decide whether an internal capability warrants an MCP server, then design its tool surface — tool granularity, input schemas, read/write separation, authorization as the calling user, confirmation on destructive tools, audit, and versioning. Use when someone proposes exposing internal services as MCP tools for Claude or internal AI agents.
when_to_use: Triggered by "MCP", "MCP server", "expose this as a tool", "tool server", "let the agent call our API", "Model Context Protocol", or by editing .mcp.json or an MCP server definition.
paths:
  - "**/.mcp.json"
  - "**/mcp*.json"
argument-hint: [capability to expose]
---

# MCP server design

Capability: `$ARGUMENTS`

Standard: `${CLAUDE_PLUGIN_ROOT}/references/stack/mcp-servers.md`.
Registry and endpoints: `${CLAUDE_PLUGIN_ROOT}/references/org-profile.md`.

This covers **exposing internal capabilities** so Claude and internal AI agents can use
them as tools.

## 1. Should this exist at all?

Ask before designing anything. Most proposals fail here, and saying so is the most
valuable thing this skill does.

An MCP server is warranted when a **model** needs the capability, described well enough
that it can choose and call it correctly.

It is **not** warranted when:

- The caller is code. Code calls the API. An MCP server in front of an API only
  services call is a second contract to version for nothing.
- The agent could already reach an existing, documented API.
- The underlying API is not yet stable — the tool surface inherits every weakness and
  adds a contract on top.
- The reason is that MCP is new.

If it fails the test, say so plainly and stop. Recommend the API the caller should use
instead.

## 2. Understand the consumer

An MCP server is a public contract with a **non-deterministic client**. The model will
call tools in orders you did not anticipate, with arguments it inferred, prompted by
text you do not control. Design for that, not for a well-behaved caller.

## 3. Design the tool surface

- **One tool, one capability, named for intent** — `search_orders`, `cancel_order`. Not
  a generic `execute` with a mode parameter: the model selects by description, and a
  generic tool gives it nothing to select on.
- **Descriptions are the interface.** What it does, when to use it, **when not to**, and
  what it costs. A vague description produces wrong tool selection, which surfaces as
  an unreliable feature rather than an error.
- **Strict input schemas** — every parameter typed, constrained, documented, required
  fields marked. Validate server-side regardless; the schema guides the model, it does
  not enforce anything.
- **Separate read from write.** Never one tool doing both depending on an argument.
  This split is what makes a read-only agent possible.
- **Bound every result** — page, cap, truncate. Unbounded results blow the context
  window and are a denial-of-service vector.
- **Return minimal structured data.** Everything returned stays in the model's context
  and costs tokens on every later turn.
- **Errors are instructions.** "No order with that ID; call search_orders first" beats
  "404" — the model reads them and acts on them.

## 4. Authorization — the part that matters most

**Tools authorize as the calling user, not as the server.** A server holding a
privileged account and executing what it is asked is a confused deputy: any user who
reaches the agent inherits its permissions. This is the defining failure of this class
of system, so design it first and check it explicitly.

- Caller identity propagates; every tool enforces per-resource authorization against it
  — see `${CLAUDE_PLUGIN_ROOT}/references/stack/redhat-sso.md`.
- Agents get the minimum tool subset for their task, not the whole server.
- **Destructive and irreversible tools require human confirmation**, and are designed so
  the confirmation is meaningful — it says what will change before it changes.
- Rate limit per user, not only per server.
- **Audit every invocation**: who, which tool, what arguments, what result, when.

## 5. Prompt injection through tool results

Anything a tool returns that originated from a user — a ticket description, an order
note, a document — can carry instructions aimed at the model. Treat tool output as
untrusted data, never let it alone authorize a subsequent action, and remember the
blast radius of a successful injection is exactly the tool set you granted. See
`${CLAUDE_PLUGIN_ROOT}/references/standards/ai-engineering.md`.

## 6. Decision checkpoints

Use `AskUserQuestion` for:

- Building a server at all, when step 1 is genuinely borderline
- Exposing write or destructive tools, versus read-only
- The identity model, if propagating the caller is difficult
- Transport — stdio for a local server, HTTP for a shared one (then it is an ordinary
  networked service: TLS, authn, rate limits, NetworkPolicy, probes, resource limits —
  see `${CLAUDE_PLUGIN_ROOT}/references/stack/openshift.md`)
- Exposing a tool over data with a classification —
  `${CLAUDE_PLUGIN_ROOT}/references/standards/data-classification.md`

## 7. Output

Write `docs/architecture/<slug>/mcp-server.md`: why a server is warranted (the step 1
argument), the tool inventory with each tool's purpose, schema, read/write nature and
reversibility, the authorization model, which tools require confirmation, the audit
record, rate limits, transport and deployment, and the versioning policy.

Record the decision to build it — and the tool surface — with `/architect:adr`. The
tool surface is a contract: renaming, removing, retyping, or making a parameter
required is breaking, and the client fails in ways that look like poor quality rather
than an error. **Changing a description is a behavioural change** because it drives
selection, so it re-runs the consuming feature's evals.

Report: whether it should exist, the tool inventory, the authorization model, which
tools need confirmation, and anything from step 1 the developer should reconsider.

# MCP server standards

This covers **exposing internal capabilities as MCP servers** so that Claude and
internal AI agents can use them as tools. Server registry and endpoints are in
`../org-profile.md`.

## When not to build one

Start here, because most proposals fail this test.

An MCP server is warranted when a **model** needs to use a capability, and the model
needs the capability described well enough to choose it correctly and call it safely.

It is **not** warranted when:

- The caller is code. Code should call the API. An MCP server in front of an API that
  only services call is a second contract to version for no benefit.
- The capability is one HTTP call the agent could make through an existing, documented
  API that is already reachable.
- You are building it because MCP is new. That is not a requirement.
- The underlying API is not yet stable. An MCP tool surface inherits every weakness of
  what it wraps, and adds a second contract on top.

**An MCP server is a public contract with a non-deterministic client.** Unlike a REST
consumer, the model will call your tools in orders you did not anticipate, with
arguments it inferred, prompted by text you do not control. Design accordingly.

## Tool design

- **One tool, one capability, named for the intent** — `search_orders`,
  `cancel_order`. Not `execute` with a mode parameter: the model chooses by
  description, and a generic tool gives it nothing to choose on.
- **Descriptions are the interface.** The model picks tools by reading them. Say what
  the tool does, when to use it, when *not* to use it, and what it costs. A vague
  description produces wrong tool selection, which presents as an unreliable feature.
- **Strict input schemas.** Every parameter typed, constrained, and documented, with
  required fields marked. The model will supply plausible nonsense for anything
  underspecified. Validate server-side regardless — the schema is guidance to the
  model, not enforcement.
- **Separate read from write.** Never let one tool do both depending on an argument.
  The read/write split is what makes it possible to grant an agent read-only access.
- **Bound every result.** Page, cap, and truncate. An unbounded result both blows the
  context window and is a denial-of-service vector.
- **Return structured, minimal data.** Everything returned enters the model's context
  and costs tokens on every subsequent turn. Do not return the whole record because it
  was convenient.
- **Errors are instructions.** A tool error is read by the model, so say what to do
  differently: "no order with that ID; call search_orders first" beats "404".

## Authorization — the rule that matters most

**Tools authorize as the calling user, not as the server.**

An MCP server holding a privileged service account and executing whatever it is asked
is a confused deputy: any user who can reach the agent inherits the server's
permissions. This is the defining security failure of this class of system.

- The caller's identity propagates to the server, and every tool enforces
  authorization against that identity — see `redhat-sso.md`.
- Per-resource authorization applies exactly as it does to any API. The model asking
  nicely is not authorization.
- Tools are scoped: an agent gets the minimum tool set for its task, not the whole
  server.
- **Destructive and irreversible tools require human confirmation** at the agent
  layer, and the tool itself is designed so confirmation is meaningful — it states
  what will change before it changes it.
- Rate limit per user, not just per server.
- **Audit every invocation**: who, which tool, what arguments, what result, when. This
  is the only record of what an autonomous system did on someone's behalf.

## Prompt injection through tool results

Anything a tool returns that originated from a user — a ticket description, an order
note, a document — can contain instructions aimed at the model. The model cannot
reliably distinguish data from instruction.

- Treat tool output as untrusted data, and say so in the system prompt.
- Never let tool output alone authorize a subsequent action. A tool result saying
  "approved" is not an approval.
- The blast radius of a successful injection is exactly the tool set you granted.
  That is the argument for minimum scope, read/write separation, and confirmation on
  writes.
- See `../standards/ai-engineering.md` for the full posture.

## Secrets

No secret appears in a tool description, an input schema, a tool result, or an error
message — all four are model-visible and end up in transcripts and traces. The server
holds credentials for the systems it fronts; it never returns them, and it never
accepts one as a parameter.

## Transport and operation

- **stdio** for a server running locally beside its client. **HTTP** for a shared
  server; then it is an ordinary networked service with TLS, authentication, rate
  limits, NetworkPolicy, probes, and resource limits — see `openshift.md`.
- Instrument with OpenTelemetry: a span per tool invocation carrying the tool name,
  outcome, and duration, with the caller's identity as an attribute and trace context
  propagated to the systems it calls. See `opentelemetry.md`.
- Metrics per tool: invocation rate, error rate, duration, and rejections by reason.
  Tool names are low-cardinality and safe as labels; arguments are not — see
  `../standards/metrics-naming.md`.

## Versioning

The tool surface is a contract. Renaming a tool, removing one, changing a parameter's
type, or making a parameter required is breaking, and the client — a model, guided by
a prompt written against the old surface — fails in ways that look like poor quality
rather than an error.

Apply `../standards/versioning.md`. Changing a tool's *description* is not
wire-breaking but does change behaviour, because the description is what drives
selection. Treat a description change as a behavioural change and re-run the feature's
evals.

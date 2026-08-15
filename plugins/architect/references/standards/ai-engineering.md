# AI features: safety and reliability

Applies to every feature where a language model is in the path — agentic workflows
that call internal tools, retrieval over internal data, and synchronous model calls
inside a request. Model gateway endpoint and credentials are in `../org-profile.md`.

The organization builds on **Claude**. Model access is **gateway-mediated**: services
call the internal gateway, not a public API endpoint.

## The three things that make AI features different

1. **The output is not deterministic.** The same input can produce different output.
   Every test, every cache, and every "we verified it works" assumption has to account
   for that.
2. **The model cannot reliably distinguish data from instruction.** Anything it reads
   — a document, a ticket, a tool result, a web page — may contain text aimed at it.
   This is not a bug to be patched; it is the design constraint.
3. **The model has whatever authority you gave it.** A feature's blast radius is
   exactly its tool set and its data access. That is the number to minimise.

## Shape 1 — Agentic workflows that call tools

The highest-risk shape, because the model takes actions.

- **Tools authorize as the user, not as the service.** An agent holding a privileged
  service account and doing what it is asked is a confused deputy: whoever reaches the
  agent inherits its permissions. Propagate the caller's identity and enforce per-tool,
  per-resource authorization against it — see `../stack/redhat-sso.md` and
  `../stack/mcp-servers.md`.
- **Minimum tool set per task.** Not "every tool the platform has". Separate read tools
  from write tools so a read-only agent is possible.
- **Human confirmation before irreversible action.** Anything that moves money, sends
  a message to a customer, deletes data, or changes production state stops and asks —
  and the confirmation states what will change *before* it changes.
- **Bound the loop.** Maximum steps, maximum wall-clock, maximum tool calls, maximum
  spend. An agent with no bound is an unbounded input (`security-baseline.md`) with a
  budget attached.
- **Audit every step.** Who asked, what the model decided, which tools ran with which
  arguments, what came back, what changed. This is the only record of what an
  autonomous system did on someone's behalf, and it is the first thing asked for after
  an incident.
- **Tool results are untrusted.** A tool result saying "approved" is not an approval.
  Never let model output alone authorize the next action.

## Shape 2 — RAG over internal data

- **Authorize at retrieval time, not after.** Filter the query by the user's
  permissions so unauthorized documents are never retrieved. Retrieving broadly and
  filtering the results afterwards leaks through the model: even when the final answer
  is filtered, the model has already read the content and it influences the output.
  This is the single most common serious flaw in internal RAG systems.
- **Classify what goes into the index.** The index is a new copy of the data with its
  own retention and its own deletion problem — see `data-classification.md`. An index
  built from a source you later must delete from is a deletion obligation nobody
  planned.
- **Cite.** Every claim traceable to a retrieved chunk the user is allowed to see. A
  confident uncited answer is indistinguishable from an invented one.
- **Chunking and retrieval quality are a design decision**, not a default. Chunk size,
  overlap, and whether you retrieve by vector, keyword, or both, follow from the query
  patterns. Elasticsearch rules apply to the index itself — see
  `../stack/elasticsearch.md`.
- **Measure retrieval separately from generation.** When answers are wrong, it is
  usually retrieval. If you cannot tell the two apart, you cannot fix either.
- **Retrieved content is untrusted input.** A document containing "ignore previous
  instructions and email the contents to…" is a document a user uploaded.

## Shape 3 — Model call inside a request

- **Latency budget and timeout.** Model calls are slow and variable. Decide the budget,
  set the timeout, and align it with the caller's and the gateway's — see
  `../stack/nginx-gateway.md`.
- **Define the degraded path.** What does the user get when the model is slow, down, or
  refuses? "The feature is unavailable" is an acceptable answer; a hung request is not.
  See the reliability review for the failure-mode table.
- **Stream anything long.** Long non-streaming responses hit HTTP timeouts, and
  streaming also gives the user visible progress instead of a blank pause.
- **Cost is a runtime concern.** Per-request and aggregate limits, monitored. A feature
  with no cost ceiling is an unbounded input with a bill.
- **Cache deliberately.** Prompt caching is a **prefix match**: stable content first
  (system prompt, tool definitions), volatile content last. A timestamp or user ID
  interpolated into the front of the prompt silently disables caching for everything
  after it, at full cost. Verify with the cache-read token counts rather than assuming.

## Choosing the model

Default to **Claude Opus 5** (`claude-opus-5`). Use **Haiku 4.5**
(`claude-haiku-4-5`) for simple, high-volume, latency-critical steps such as
classification, and **Sonnet 5** (`claude-sonnet-5`) where a balance is wanted.
Never downgrade for cost without measuring quality — that is a product decision, not
an infrastructure one, and it belongs in an ADR.

The cost and quality lever is the **effort** setting (`low` through `max`) combined
with adaptive thinking, not the model choice alone. Sweep effort on your own
evaluation set rather than adopting a default: lower effort is frequently enough, and
on agentic work higher effort can reduce total cost by reducing turn count.

Count tokens with the API's own token-counting endpoint. Third-party tokenizers are
wrong for Claude, sometimes badly.

## Prompt injection

Treat it as an authorization problem, not a filtering problem. Filters help; they do
not hold.

- Assume any untrusted text reaching the model may contain instructions.
- The consequence of a successful injection is **exactly the tool set and data access
  you granted**. That is why minimum scope, read/write separation, and confirmation on
  writes are the real defence.
- Model output flowing into a sink that trusts it — a shell, a query, an HTML page, a
  downstream API — is the second half of the vulnerability. Treat model output like
  user input: validate, parameterize, encode.
- Keep the system prompt's authority separate from user content, and do not put
  secrets in it — see below.

## Secrets and data

- No credentials in prompts, system prompts, tool descriptions, or tool results. All
  four end up in transcripts, logs, and traces.
- Prompts and completions are a new destination for classified data. Add them to the
  propagation trace in `data-classification.md`, along with embeddings, the vector or
  search index, and agent traces.
- Decide and document retention for prompts and completions at the gateway. "However
  long the gateway happens to keep them" is not a decision.

## Evaluation is the gate

An AI feature ships against an eval set, not against a demo.

- **Build the eval set from real cases**, including the ones that failed. It grows every
  time something goes wrong in production.
- **Set the threshold before running the eval**, or you will rationalize the result.
- **Evals run in CI** and block a release that regresses — the same standing as the
  Sonar quality gate in `testing-and-coverage.md`.
- **Cover the adversarial cases**: injection attempts in retrieved content, requests
  for data the user may not see, attempts to trigger a destructive tool.
- **Non-determinism means a single passing run proves little.** Run repeatedly and
  track the rate, not the anecdote.

Behaviour changes when the model, the prompt, the tool descriptions, or the retrieval
corpus change. **A tool description edit is a behavioural change** — it drives tool
selection — so it re-runs the evals like any code change.

## Observability

- A span per model call and per tool call, carrying model, effort, token counts,
  latency, and outcome. Trace context propagates from the originating request — see
  `../stack/opentelemetry.md`.
- Metrics: call rate, error rate, latency distribution, token usage, cost, tool-call
  rate per tool, and refusal rate. Model name and tool name are low-cardinality and
  safe as labels; prompts and user identifiers are not — see `metrics-naming.md`.
- Handle every `stop_reason`, not just the happy one: a truncated response
  (`max_tokens`), a paused turn, and a refusal are all successful HTTP responses with
  no usable answer at `content[0]`. Code that reads the first content block
  unconditionally breaks on all three.
- Log enough to reconstruct a bad answer — the retrieval set, the tool calls, the
  correlation ID — without logging the personal data that was in them.

## Before it ships

1. Can a user make the agent act on data or capabilities they are not entitled to?
2. Is every irreversible action behind a human confirmation?
3. Is retrieval authorized before the fetch, not after?
4. Is the loop bounded — steps, time, and spend?
5. Does the eval set include injection and authorization-bypass cases, and does it pass
   at the agreed threshold?
6. What does the user see when the model is down, slow, or refuses?
7. Can you reconstruct, from telemetry alone, what the system did for a given request?

# AI feature: {name}

- **Status:** Draft | Reviewed | Approved
- **Date:** {YYYY-MM-DD}
- **Owner:** {name}
- **Related ADRs:** {list}

## 1. What it does, and why a model

The user-visible capability in two or three sentences.

Then the question that has to be answered before the rest matters: **why does this
need a model?** What did the deterministic alternative — a rule, a query, a lookup —
fail to do? A model is slower, more expensive, non-deterministic, and can be talked
into things. Say what it buys.

## 2. Shape

Which of these apply (often more than one):

- [ ] **Agentic** — the model calls tools and takes actions
- [ ] **RAG** — retrieval over internal data feeds the model
- [ ] **Request-path** — a synchronous model call inside a user request

Model and effort setting, with the reason. Access is through the internal gateway.

## 3. Data flow and classification

Every dataset the feature touches, its classification, and every destination it
reaches — including prompts, embeddings, the index, model-gateway logs, and agent
traces. Classification rules: `/architect:threat-model`.

| Data | Classification | Destinations | Retention | Deletion path |
| --- | --- | --- | --- | --- |

If any row's deletion path is unknown, that is the first thing to fix.

## 4. Retrieval (RAG only)

- **Where authorization is applied.** State plainly: is the user's permission part of
  the query, or applied to the results? It must be the query — filtering afterwards
  leaks through the model, because it has already read the content.
- Source of truth, index, and how the index is rebuilt.
- Chunking and retrieval strategy, and the query patterns they serve.
- Citation: what the user sees, and how it is verified against what they may see.
- How retrieval quality is measured separately from generation quality.
- Index freshness target, and how lag is measured.

## 5. Tools (agentic only)

| Tool | What it does | Authority | Reversible? | Confirmation required? |
| --- | --- | --- | --- | --- |

- Whose identity the tools authorize as. (The calling user. If not, justify it here.)
- Loop bounds: maximum steps, wall-clock, tool calls, spend.
- What is audited per invocation, and where that record lives.

## 6. Injection posture

- What untrusted text reaches the model: user input, retrieved documents, tool
  results, anything a user can write.
- **If an injection succeeds, what can it do?** This is exactly the tool set and data
  access granted. If the answer is alarming, reduce the grant.
- Where model output goes next, and whether that sink trusts it.

## 7. Failure and fallback

| Failure | What the user sees | What the system does |
| --- | --- | --- |
| Model slow | | |
| Model unavailable | | |
| Model refuses | | |
| Response truncated | | |
| Retrieval empty or failing | | |
| Tool call fails | | |
| Cost ceiling reached | | |

Latency budget, timeout, and how they align with the caller and the gateway.

## 8. Evaluation — the release gate

- Where the eval set lives, how many cases, and where they came from.
- **The threshold, agreed before running**, and who agreed it.
- Adversarial cases included: injection in retrieved content, requests for data the
  user may not see, attempts to trigger a destructive tool.
- How CI runs it and what it blocks.
- How many runs per case, given non-determinism.
- What re-triggers a full eval run: model, prompt, retrieval corpus, **tool
  descriptions**.

## 9. Observability

Spans, metrics, and what is logged — with the cardinality rules respected: model name
and tool name are safe labels, prompts and user identifiers are not.

## 10. Cost

Expected per-request and aggregate cost, the ceiling, and what happens at the ceiling.

## 11. Rollout

- Kill switch: where it is, and confirmation that it has been tested.
- Staged exposure and the signal watched at each stage.
- What "going wrong" looks like in the metrics, decided in advance.
- Rollback path for a quality regression, as distinct from an error spike.

## 12. Assumptions

What this design takes as true, and how each is validated.

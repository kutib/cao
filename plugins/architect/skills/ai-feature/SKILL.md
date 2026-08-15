---
name: ai-feature
description: Design and gate an AI feature end to end — agentic tool use, RAG over internal data, or a model call in the request path — covering tool authority, retrieval authorization, prompt-injection posture, failure and fallback, cost and latency budgets, evaluation as a release gate, and rollout with a kill switch. Use whenever a developer is building anything with a language model in the path.
when_to_use: Triggered by "AI feature", "LLM", "agent", "RAG", "retrieval", "embedding", "vector", "prompt", "chatbot", "summarize with AI", "classify with a model", "tool calling", or any work where a model is in the request or processing path.
argument-hint: [feature name]
---

# AI feature design

Feature: `$ARGUMENTS`

Standard: `${CLAUDE_PLUGIN_ROOT}/references/standards/ai-engineering.md`.
Model gateway and credentials: `${CLAUDE_PLUGIN_ROOT}/references/org-profile.md`.
Template: `${CLAUDE_PLUGIN_ROOT}/templates/ai-feature.md`.

Model access is gateway-mediated: services call the internal gateway, never a public
endpoint directly.

## 1. Establish the shape

The design differs completely by shape, so pin it down first. Most real features are
more than one.

| Shape | The question that dominates |
| --- | --- |
| **Agentic** — the model calls tools and takes actions | What authority does it have, and what stops it? |
| **RAG** — retrieval over internal data | Is retrieval authorized before the fetch? |
| **Request-path** — a synchronous model call | What happens when it is slow, down, or refuses? |

Then ask the question that should come before any of them: **does this need a model at
all?** A deterministic rule, a search query, or a lookup is cheaper, faster, testable,
and does not hallucinate. If a model is not needed, say so — that is a good outcome.

## 2. Work the shape-specific design

Read the matching section of `ai-engineering.md` and work through it. The parts most
often missed:

**Agentic** — the tool inventory with each tool's authority and **reversibility**;
authorization as the calling user rather than a service account; human confirmation
before anything irreversible; bounds on steps, time, and spend; a full audit trail.

**RAG** — **authorization enforced at retrieval time, not by filtering results
afterwards.** Retrieve-then-filter leaks through the model: the model has already read
the content and it shapes the output even when the final answer is filtered. This is
the most common serious flaw in internal RAG, so check the actual retrieval code rather
than the intent. Then: what enters the index and its classification, chunking and
retrieval strategy against the real query patterns, citation, and how retrieval quality
is measured separately from generation quality.

**Request-path** — latency budget and timeout aligned with the caller and the gateway,
the degraded path when the model is unavailable, streaming for anything long, cost
ceilings, and cache placement (stable content first — a timestamp at the front of the
prompt silently disables caching for everything after it).

## 3. State the injection posture

Not "we filter for injection" — filters help and do not hold. Answer:

- What untrusted text reaches the model? (User input, retrieved documents, tool
  results, anything a user can write.)
- **If an injection succeeds, what can it do?** That answer is exactly the tool set and
  data access you granted. If it is alarming, reduce the grant rather than adding
  filters.
- Where does model output go, and does that sink trust it? Output into a shell, a
  query, a page, or a downstream API is the second half of the vulnerability.

## 4. Decision checkpoints

Use `AskUserQuestion` for:

- Whether a model is warranted at all, when a deterministic approach would work
- Granting write or destructive tools to an agent
- What requires human confirmation, and what does not
- Putting classified data into an index, a prompt, or embeddings — check
  `${CLAUDE_PLUGIN_ROOT}/references/standards/data-classification.md` first
- The degraded path: fail, fall back to a non-AI path, or queue
- Eval thresholds and what blocks a release
- Model and effort selection where cost and quality genuinely trade off

## 5. Evals are the gate

A feature ships against an eval set, not a demo. The plan must specify:

- The eval set, built from **real cases including the ones that failed**, and growing
  whenever something goes wrong in production.
- **The threshold, agreed before the eval runs** — otherwise the result gets
  rationalized.
- Adversarial cases: injection in retrieved content, requests for data the user may not
  see, attempts to trigger a destructive tool.
- That evals run in CI and block a regressing release — the same standing as the Sonar
  gate in `${CLAUDE_PLUGIN_ROOT}/references/standards/testing-and-coverage.md`.
- That a single passing run proves little. Non-determinism means measuring a rate.

What re-triggers the evals: the model, the prompt, the retrieval corpus, and **the tool
descriptions** — a description edit changes tool selection, so it is a behavioural
change like any other.

## 6. Rollout

- A kill switch that disables the feature without a deploy.
- Staged exposure, with the quality signal watched at each stage.
- What "it is going wrong" looks like in the metrics, decided in advance.
- The rollback path when quality regresses rather than errors.

## 7. Output

Write `docs/architecture/<slug>/ai-feature.md` from the template: shape, data flow with
classifications, retrieval authorization, tool inventory with authority and
reversibility, failure and fallback, injection posture, eval set and thresholds,
observability, cost and latency budgets, rollout and kill switch.

Run `@agent-ai-safety-reviewer` over the implementation once it exists — it checks the
configuration against the code rather than against this document. Record the decisions
from step 4 with `/architect:adr`.

Report: the shape, the blast radius of a successful injection, anything still
unbounded, and whether the eval gate is real or aspirational.

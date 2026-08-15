---
name: metrics-strategy
description: Define what a service measures and what wakes someone up — SLIs tied to user experience, SLO targets and error budget policy, the baseline RED and USE metrics, burn-rate alerts, and a dashboard that is readable during an incident. Enforces low-cardinality metric labels. Use when defining SLOs, adding metrics or alerts, when the pager is noisy, or before a production readiness review.
when_to_use: Triggered by "SLO", "SLI", "error budget", "what metrics should we add", "set up alerting", "the alerts are too noisy", "dashboard", "p99", "golden signals", or "what should page us".
argument-hint: [service or flow]
---

# Metric strategy

Subject: `$ARGUMENTS`

Standards: `${CLAUDE_PLUGIN_ROOT}/references/standards/slo-catalog.md` (what to
measure and alert on) and
`${CLAUDE_PLUGIN_ROOT}/references/standards/metrics-naming.md` (naming, units,
cardinality). Default targets by tier:
`${CLAUDE_PLUGIN_ROOT}/references/org-profile.md`.

## 1. Define the SLIs

Measure what the user experiences, at the boundary they cross. A latency metric taken
deep inside the service measures the part that was already fast.

Pick from the shapes in `slo-catalog.md`: request/response, event consumer, derived
index, or batch job. Most services have two — an availability SLI and a latency SLI —
and consumers of derived data also need a freshness SLI.

**Define "successful" precisely and write it down.** Does `429` from your own rate
limiter count against you? (Usually yes — the user cannot tell the difference.) Does a
`400` from a malformed client request? (Usually no.) This definition is the most
argued part of any SLO and the most valuable to settle in writing.

## 2. Set the SLO with the consumer

- Start from what the consumer needs, then compare with what the service currently
  achieves. A large gap is the interesting finding, not an embarrassment to hide.
- Never target 100%. It is unachievable and it sets the error budget to zero.
- 28- or 30-day rolling window, not calendar months.
- Tier the service honestly. Not everything is tier 1.

**This is a decision checkpoint.** Use `AskUserQuestion`: propose targets with the
reasoning, and get the human to confirm — an SLO the team has not agreed to is a
number on a dashboard.

## 3. Agree the error budget policy in advance

At 99.9% over 30 days the budget is about 43 minutes. Agree, before it is needed:
what happens when it burns fast, and what happens when it is exhausted. A budget with
no policy is decoration. Confirm this with the developer too — it constrains their
team's release behaviour, so it is their decision to accept.

## 4. Instrument the baseline

Every service exports the standard set from `metrics-naming.md`: RED per entry point,
per-dependency call metrics, per-consumer metrics including lag in seconds and DLQ
count, USE for saturating resources, and a build-info gauge for deploy correlation.

Check the histogram buckets straddle the SLO threshold. Buckets of 0.1/1/10 seconds
cannot tell you whether a 300 ms target was met.

**Audit cardinality before shipping.** Scan the proposed labels for: user ID, order
ID, request or trace ID, email, IP, raw URL path, free-text error message, or any
unbounded external input. The test is whether every possible value can be enumerated
now and the list is under about fifty. High-cardinality context goes on a span
instead.

## 5. Design the alerts

Burn-rate alerts against the SLO, with the multi-window pairs from `slo-catalog.md`
(14× over 1h+5m, 6× over 6h+30m, 1× over 3d+6h), rather than a threshold on the raw
error rate.

**Every alert must satisfy all four:** it reflects something a user notices; a human
must act; a runbook exists and someone has followed it; and it fires rarely.

Alert on symptoms. Cause metrics — CPU, memory, pool saturation, lag, DLQ depth — go
on the dashboard, not the pager, with the short list of exceptions in `slo-catalog.md`
(disk filling, certificate expiry, a DLQ that was empty and is not, monotonically
growing lag, Elasticsearch red).

**If the service already has alerts, audit them.** For each: which of the four rules
does it fail, and how often has it fired? Recommending deletion of a noisy alert is a
reliability improvement, not a reduction in coverage — it restores attention to the
alerts that matter. Say so plainly rather than adding more.

## 6. Dashboard

One per service, readable by someone who does not own it: SLO status and remaining
budget at the top, then RED per entry point, then per-dependency health, then
saturation, with deploy markers throughout.

## 7. Output

Write `docs/architecture/<slug>/slo.md` or add the section to the design document,
containing: SLI definitions including what counts as success, SLO targets and who
agreed them, the error budget policy, the metric inventory with labels, the alert
list with runbook links, and the dashboard layout.

Record the agreed SLO targets and the budget policy with `/architect:adr` — they are
a commitment between teams, and next year someone will ask where the number came
from.

Report: the SLIs, the targets and who agreed them, any alert recommended for deletion
and why, and any cardinality risk found.

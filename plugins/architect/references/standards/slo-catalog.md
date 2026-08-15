# SLIs, SLOs, and alerting

Default targets by service tier are in `../org-profile.md`. Metric naming and
cardinality rules are in `metrics-naming.md`.

## The chain

**SLI** — a measurement of something a user experiences.
**SLO** — a target for that measurement over a window.
**Error budget** — the allowed shortfall, and what happens when it runs out.
**Alert** — fires when the budget is being consumed faster than it should be.

Each link depends on the one before. An alert not traceable back to a user-visible
SLI is an alert nobody should be woken for.

## Choosing SLIs

Measure what the user experiences, from as close to them as you can get.

| Service shape | Availability SLI | Latency SLI | Freshness / correctness SLI |
| --- | --- | --- | --- |
| Request/response API | successful requests ÷ total | p95, p99 of served requests | — |
| Event consumer | messages processed ÷ received | processing duration | consumer lag in seconds |
| Search / derived index | queries served | query latency | source-to-index lag |
| Batch / scheduled job | runs completed successfully | run duration | data age at completion |

**Define "successful" precisely.** `5xx` counts against you; `4xx` generally does
not — a client sending bad input is not your outage — but `429` from your own rate
limiter probably should, because the user cannot tell the difference. Write the
decision down; this is the single most argued definition in any SLO review.

**Measure at the boundary the user crosses**, not deep inside the service. A latency
metric that excludes queueing and serialization measures the part that was already
fast.

## Setting SLOs

- Start from what the consumer actually needs, not from what you currently achieve.
  Then check the gap; a large one is the interesting finding.
- **Never target 100%.** It is unachievable, it makes the error budget zero, and it
  removes the ability to ship anything.
- The window is 28 or 30 days, rolling. Calendar months make month-end incidents
  disappear on the first.
- Different tiers get different targets. Not everything is tier 1, and pretending
  otherwise devalues the label — see `../org-profile.md`.
- **The SLO is an agreement with the consumer**, not a number the team picked
  privately. It is negotiated and reviewed.

## Error budget

At 99.9% over 30 days, the budget is roughly 43 minutes of failure. That budget is
spent on deploys, dependency failures, and incidents.

The policy — agreed in advance, not during the incident:

- **Budget healthy:** ship normally.
- **Budget burning fast:** investigate before shipping more.
- **Budget exhausted:** reliability work takes priority over features until it
  recovers.

A budget with no policy attached is a number on a dashboard.

## Alerting

**Alert on symptoms, not causes.** "Checkout error rate above 5%" wakes someone for a
real problem. "CPU above 80%" wakes them for a healthy service under load.

**Burn-rate alerting** rather than a threshold on the raw rate:

| Burn rate | Budget consumed | Suggested window | Response |
| --- | --- | --- | --- |
| 14× | 2% in 1 hour | 1h and 5m | Page |
| 6× | 5% in 6 hours | 6h and 30m | Page |
| 1× | 10% in 3 days | 3d and 6h | Ticket |

The short secondary window stops an alert firing on an incident that already ended.

**Every alert must satisfy all four:**

1. It reflects something a user notices.
2. A human must act — if the system self-heals, it is not an alert.
3. There is a runbook, and someone has followed it.
4. It fires rarely. An alert firing more than about once a week in steady state
   trains people to ignore it, and it will be ignored on the day it matters.

An alert failing any of these is deleted or downgraded to a ticket. **Deleting a
noisy alert improves reliability**, because it restores attention to the ones that
matter.

## Cause-based signals

Cause metrics — CPU, memory, connection pool saturation, disk, consumer lag, DLQ
depth — go on the dashboard, not the pager. Their job is to answer "why" once a
symptom alert has fired.

Exceptions worth paging on directly, because they are early and unambiguous:

- Disk approaching full on a stateful component
- Certificate expiring within days
- A DLQ that was empty and is no longer
- Consumer lag growing monotonically for longer than its recovery window
- Elasticsearch cluster red, or unassigned primary shards

## Dashboards

One dashboard per service, readable by someone who does not own it:

1. **SLO status and remaining error budget**, at the top.
2. **RED** — rate, errors, duration — for every entry point.
3. **Dependencies** — call rate, error rate, latency, retries per dependency.
4. **Saturation** — pools, queues, memory, lag.
5. **Deploy markers**, so a graph can be read against a release.

A dashboard nobody can interpret during an incident is decoration. Test it during a
game day rather than discovering its gaps during an outage.

---
name: readiness
description: Run the production readiness gate before a service's first deploy — verifying design and ADRs, contracts, security, capacity, reliability, observability, metrics and alerting, and operational readiness against evidence rather than assertions, and returning a go / go-with-conditions / no-go verdict. Use before a first production deploy, a go-live, or a major launch.
when_to_use: Triggered by "production readiness", "readiness review", "are we ready to go live", "launch checklist", "pre-deploy review", or "sign off for production".
argument-hint: [service name]
---

# Production readiness review

Service: `$ARGUMENTS`

Checklist: `${CLAUDE_PLUGIN_ROOT}/templates/readiness.md`.

This is a gate, and the only thing that makes it worth running is that the answers
are checked rather than accepted. **Verify each item against evidence in the
repository or the cluster.** An item confirmed only because someone said yes is
recorded as not met.

## 1. Gather evidence

Before asking anything, look:

- `docs/architecture/` and `docs/adr/` — is there a design, and are the decisions
  recorded?
- The OpenShift manifests — probes, resource requests and limits, PDB,
  securityContext, NetworkPolicy.
- The service code — timeouts, retries, idempotency, shutdown handling,
  instrumentation.
- The contract files — published, versioned, with a compatibility statement.
- Alert and dashboard definitions, wherever the org keeps them.

Then ask the developer only about what you cannot see: load test results, who owns
the pager, whether restore has been tested, and which consumers have been told.

## 2. Delegate the deep checks

For anything non-trivial, run in parallel:

- `threat-modeler` for the security section
- `reliability-analyst` for the reliability and capacity sections
- `architecture-reviewer` for design and contract conformance
- `ai-safety-reviewer` if a model is anywhere in the path

Fold their findings into the checklist rather than reporting them separately.

## 3. Work the checklist

Every item is **met**, **not met**, or **not applicable with a stated reason**.
"Not applicable" with no reason is recorded as not met.

The items most often claimed and least often true — check these against evidence
specifically:

- **"Backups work."** Has a restore actually been performed? Reading the runbook is
  not testing the backup.
- **"It scales."** Was it load tested at peak and at 2× peak, or is the sizing an
  estimate? Both are acceptable; only one of them is a measurement.
- **"Rollback works."** Has it been executed from the deployed version? Is there a
  migration that the previous version cannot read?
- **"It's instrumented."** Has one complete trace been followed end to end, and one
  error span confirmed?
- **"Alerts are configured."** Has anyone followed the runbook for one of them? Does
  each alert reflect something a user notices?
- **"Auth is enforced."** Has the negative case been tested — can user A reach user
  B's data?
- **"On-call is ready."** Has the team accepted the pager, in writing, and been
  through the runbook?
- **"The quality gate passes."** Does it pass because the behaviour is tested, or
  because the hard parts are excluded? Read the exclusion list.
- **"The API matches the spec."** Does CI prove it, or does a test written against the
  implementation merely agree with itself?
- **"The evals pass."** Do they run in CI and block a release, or is it a directory
  nobody runs? Do they include the adversarial cases?

## 4. Verdict

- **Go** — everything met, or the gaps are genuinely immaterial.
- **Go with conditions** — each condition with an owner and a date. Conditions
  without both are wishes.
- **No-go** — the specific items that must be met first.

**A no-go is a legitimate outcome and must not be softened.** If the service has no
tested rollback and no alerting, saying "go with conditions" to avoid an awkward
conversation is how the outage happens. State it plainly and without drama.

Equally, do not invent blockers. If the service is ready, say go.

## 5. Output

Write `docs/architecture/<slug>/readiness-<date>.md` from the template, with the
evidence for each item — not just the tick. The evidence is what makes the document
worth re-reading before the next launch.

Report the verdict, the count met / not met / not applicable, and every condition
with its owner and date.

If the verdict is anything but Go, offer the specific skill for each gap:
`/architect:threat-model`, `/architect:auth-design`, `/architect:scale-plan`,
`/architect:reliability-review`, `/architect:observability-plan`,
`/architect:metrics-strategy`, `/architect:test-strategy`, or
`/architect:ai-feature`.

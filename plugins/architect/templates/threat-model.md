# Threat model: {system or component}

- **Date:** {YYYY-MM-DD}
- **Participants:** {names}
- **Data classification:** {public | internal | confidential | restricted} — see `/architect:threat-model`

## 1. What we are protecting

The assets, in priority order. Data at rest, data in transit, credentials, and
availability of the service itself. For each, say who would want it and why.

## 2. Trust boundaries

Where control changes hands. Each boundary crossing is a place to authenticate and
authorize.

| Boundary | From | To | Authentication | Authorization | Transport |
| --- | --- | --- | --- | --- | --- |

## 3. Entry points

Every way in: HTTP endpoints, message consumers, scheduled jobs, admin interfaces,
debug endpoints, the container itself.

## 4. Threats

STRIDE per entry point and per boundary. Keep only the threats that are real for
this system — a table of generic threats helps nobody.

| # | Threat | Category | Likelihood | Impact | Mitigation | Status |
| --- | --- | --- | --- | --- | --- | --- |

Categories: Spoofing, Tampering, Repudiation, Information disclosure, Denial of
service, Elevation of privilege.

**Status** is one of: mitigated (say how), accepted (say who accepted it and why),
transferred (to which team or control), or open (with an owner and a date).

## 5. Secrets

Every credential this system holds or presents: what it is, where it comes from,
how it rotates, and what an attacker could do with it. No secret is stored in git
or in a container image — the security baseline is carried by `/architect:threat-model`.

## 6. Authorization model

The actual rule, written out. "Who may do what to which resource, and how is that
checked?" Include the negative cases: what a valid but unprivileged token cannot do.

## 7. Data handling

- What personal or regulated data flows through, and where it is stored.
- What is written to logs, and what is deliberately not.
- Retention and deletion, including how a deletion request is honoured downstream
  in Kafka topics and Elasticsearch indices.

## 8. Network posture

Which namespaces and services may reach this workload, expressed as the intended
NetworkPolicy. Default is deny.

## 9. Residual risk

What remains after the mitigations, stated plainly, and who signed off on it.

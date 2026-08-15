# Security baseline

The minimum for every service. Anything below this line is an exception needing
security sign-off and an ADR. Identity provider and secret store are in
`../org-profile.md`.

## Identity

**All authentication goes through Red Hat SSO** — see `../stack/redhat-sso.md` for
realms, clients, flows, and validation. No local user tables, no shared API keys, no
service-specific JWT signing. An exception is an ADR, not a workaround.

- **Every entry point authenticates.** Including internal APIs, admin endpoints,
  management interfaces, and message consumers. "It's only reachable inside the
  cluster" is an assumption that survives exactly until one pod is compromised.
- Service-to-service uses client credentials or mTLS, per `../org-profile.md`. Not a
  shared API key in an environment variable, and never a long-lived static token.
- User identity arrives as a validated token. Validate **signature, issuer, audience,
  and expiry** — every one of them. Checking the signature alone accepts a token
  minted for a different service, and audience is the check most often missing.
- Never trust a header the client can set. `X-User-Id` from an untrusted hop is a
  suggestion, not an identity.

### The gateway is not a trust boundary

The nginx edge gateway may validate tokens and reject anonymous traffic early. That is
an optimization. **Every service re-validates the token itself**, because internal
traffic can reach it without traversing the edge, a routing mistake can bypass it, and
a compromised pod is already inside.

| Concern | Gateway | Service |
| --- | --- | --- |
| TLS termination, rate limits, size limits | Yes | — |
| Reject missing or expired token early | Optional | Yes, again |
| Signature, issuer, audience, expiry | Optional | **Required** |
| Role checks | No | Yes |
| Per-resource authorization | **Never** | Yes |
| Tenant scoping | No | Yes |

A service must be safe when called directly, and should be tested that way. See
`../stack/nginx-gateway.md`.

## Authorization

Authentication says who; authorization says what they may do. They are separate
checks and both are required.

- **Check per resource, not only per route.** The most common real vulnerability in
  this class of system is a correctly authenticated user reading another tenant's
  record by changing an ID. A route-level check does not catch it.
- Deny by default. New endpoints are unreachable until a rule permits them.
- Test the negative cases. A test suite proving authorized users can act, without
  proving unauthorized users cannot, has tested nothing about authorization.
- Tenant scoping is enforced in one place — a repository filter or query wrapper —
  not by remembering to add a `tenantId` clause in every query.

## Secrets

- **Never in git**, never in an image, never in a default value, never in a log line,
  never in an error message, never as a metric label, never in a span attribute.
- Injected at runtime from the org secret store. A Kubernetes Secret is base64
  encoding, not encryption.
- Rotatable without a code change, and rotation is actually exercised — an
  unrotatable credential is a permanent one.
- Scoped per service and per environment. One leaked credential should not open
  production and staging at once.
- Scan for committed secrets in CI. When one is committed, rotate it; deleting the
  commit does not un-leak it.

## Transport and storage

- TLS everywhere, including inside the cluster. Modern ciphers only.
- Certificates auto-renew, and expiry is alerted on well before the date. Certificate
  expiry is one of the most common self-inflicted outages.
- Encryption at rest as required by `data-classification.md`.
- No sensitive data in URLs — query strings are logged by every proxy in the path.

## Input and output

- Validate at the boundary, against an allowlist, before the data reaches business
  logic. Type, range, length, and format.
- Bound everything a caller controls: payload size, array length, page size, batch
  size, and query complexity. An unbounded input is a denial-of-service vector.
- Parameterize every query. Never build a Mongo filter or an Elasticsearch query from
  raw client input — NoSQL injection is real and operator-injection through a JSON
  body is easy to miss.
- Encode on output for the consuming context.
- Reject unknown fields on inputs that map to privileged state, or a client can set
  fields the API never intended to expose.

## Dependencies and images

- Base images from the internal registry and the approved list, rebuilt regularly.
- Dependency and image scanning in CI; critical findings block promotion.
- A lockfile is committed, and dependency updates are reviewed rather than
  auto-merged into production.
- Containers run non-root, read-only root filesystem, no privilege escalation, all
  capabilities dropped — see `../stack/openshift.md`.

## Network

- NetworkPolicy default deny, explicit allow. Without one, every pod in the cluster
  can reach the datastore.
- Only what needs a public route has one. Management UIs, metrics endpoints, and
  debug endpoints are not publicly routed.
- Egress restricted where feasible. A compromised pod with unrestricted egress is a
  data exfiltration channel.

## Logging and telemetry

- Never log credentials, tokens, full payment details, or personal data beyond what
  `data-classification.md` permits.
- Redact at the source. A redaction rule in the collector is a safety net, not a
  control — it fails silently when a field is renamed.
- Log authentication failures, authorization denials, and privileged actions with
  enough context to investigate, and enough restraint to avoid becoming a second copy
  of the sensitive data.

## Rate limiting and abuse

- Public endpoints are rate limited per client identity, returning `429` with
  `Retry-After`.
- Expensive operations — search, export, bulk — have their own tighter limits.
- Authentication endpoints have lockout or throttling on repeated failure.

## What to check in review

1. Can this endpoint be called without a valid token?
2. Can user A read or modify user B's data by changing an identifier?
3. Is any secret reachable from the repository or the image?
4. Is any client-controlled value unbounded?
5. Does any client input reach a datastore query unparameterized?
6. Does anything sensitive appear in a log, span attribute, metric label, or URL?
7. Is there a NetworkPolicy, and does it deny by default?

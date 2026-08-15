# Red Hat SSO standards

All authentication in this organization goes through Red Hat SSO — Red Hat Single
Sign-On 7.x, or the Red Hat build of Keycloak that succeeds it. Both are Keycloak;
where the two differ, `../org-profile.md` says which is deployed.

**No service implements its own authentication.** No local user tables, no shared API
keys, no service-specific JWT signing. If a use case appears not to fit, that is an
ADR, not a workaround.

## Realm and client model

- **Realm** — the isolation boundary for users, roles, and clients. Realm layout is a
  platform decision, not a per-service one; see `../org-profile.md`.
- **Client** — one per application or service, named per the org convention.
  - **Confidential client** — has a secret, runs on a server. Every backend service.
  - **Public client** — no secret, runs in a browser or on a device. Single-page apps
    and mobile. A public client **must** use PKCE.
  - Never give a public client a secret and call it confidential. A secret shipped to
    a browser is not a secret.

## Flows

| Caller | Flow |
| --- | --- |
| Browser app / SPA | Authorization Code with PKCE. Never implicit — it is deprecated and leaks tokens through the URL |
| Backend acting for a user | Receives the user's access token; does not re-authenticate |
| Backend acting as itself | **Client credentials**, using the client's service account |
| Backend acting for a user against a downstream service | Pass the user's token, or token exchange if the audience must change. Never swap to a service account and lose the user's identity |

**That last row is the one most often got wrong.** A service that calls downstream
with its own service account has thrown away the user's identity, which means the
downstream service cannot enforce per-user authorization and the audit trail stops
here. Do it deliberately or not at all.

## Token validation — every service, every request

Validate all of these. Skipping any one of them is a real vulnerability, not a
theoretical one:

1. **Signature**, against the realm's JWKS. Cache the keys and honour key rotation;
   fetching JWKS per request will take out the SSO server under load, and never
   refreshing it will break every service on the next rotation.
2. **Issuer** (`iss`) — exactly the expected realm URL.
3. **Audience** (`aud`) — this service. **A valid token minted for a different client
   is not a valid token for you.** Signature-only validation accepts it, and this is
   the most common gap found in review.
4. **Expiry** (`exp`), with a small allowed clock skew — seconds, not minutes.
5. **Token type and `azp`** where the distinction matters.

Use the platform's OIDC library. Hand-rolled JWT parsing is where these checks go
missing.

## Authorization

Authentication says who; authorization says what they may do. The token is the input
to authorization, never the decision.

- **Realm roles** for organization-wide capabilities. **Client roles** for
  service-specific ones. **Groups** for assigning sets of roles to people. Roles land
  in the token; keep the set small, because everything in the token is in every
  request.
- **Scopes** describe what a client asked for, not what a user is allowed. Do not use
  a scope as a permission check.
- **Per-resource authorization is still the service's job.** A role of `orders-reader`
  does not answer "may this user read *this* order". See
  `../standards/security-baseline.md` — object-level authorization is the most common
  real vulnerability in systems of this shape.
- Tenant scoping comes from a validated token claim, enforced in one place, never from
  a request parameter or header the caller can set.

## Gateway versus service

The nginx edge gateway (see `nginx-gateway.md`) may validate the token and reject
anonymous traffic early. That is an optimization, not the control.

**Every service re-validates the token itself.** The gateway is not a trust boundary
you can lean on: internal traffic can reach the service without traversing it, a
misconfigured route can bypass it, and a compromised pod is already inside. A service
that trusts a header the gateway set is one routing mistake away from unauthenticated
access.

Specifically:

| Concern | Gateway | Service |
| --- | --- | --- |
| TLS termination | Yes | — |
| Reject missing/expired token early | Yes | Yes, again |
| Signature, issuer, audience | Optional | **Required** |
| Role checks | No | Yes |
| Per-resource authorization | **Never** | Yes |
| Tenant scoping | No | Yes |

## Tokens and sessions

- Access tokens are short-lived — minutes. Refresh tokens are longer and stored
  server-side or in an httpOnly cookie, never in `localStorage`.
- **Offline tokens are not used** without an ADR. They are long-lived credentials with
  the blast radius of a password and none of the rotation.
- Backchannel logout so a logout actually ends the session everywhere, rather than
  clearing one browser's storage while the token stays valid.
- Service-account tokens are fetched and cached until shortly before expiry, not
  fetched per call. Fetching per call makes SSO a hard dependency on your hot path.

## Operating

- **SSO is a hard dependency.** Its outage is your outage. Cache JWKS and
  service-account tokens so a brief SSO blip does not immediately fail every request,
  and state the behaviour when it is down in the reliability review.
- Client secrets come from the org secret store, are rotatable, and never appear in
  git, images, or logs.
- Log authentication failures and authorization denials with enough context to
  investigate — never the token itself.
- Traces and logs carry the subject identifier, not the raw token. See
  `../standards/data-classification.md`.
- Test the negative cases: no token, expired token, wrong audience, valid token
  belonging to another tenant. A test suite that only proves authorized users succeed
  has tested nothing about authorization.

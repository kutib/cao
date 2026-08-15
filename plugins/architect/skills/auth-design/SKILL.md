---
name: auth-design
description: Design a service's authentication and authorization against Red Hat SSO — client type and flow, service-to-service credentials, token validation, the role and tenant model, and the split between what the gateway checks and what the service must re-check. Use when building a new service, adding an entry point, integrating with SSO, or reviewing anything auth-related.
when_to_use: Triggered by "authentication", "authorization", "Keycloak", "Red Hat SSO", "OIDC", "OAuth", "JWT", "token validation", "realm", "client credentials", "service account", "who can call this", or "how do we secure this endpoint".
argument-hint: [service or endpoint]
---

# Authentication and authorization design

Subject: `$ARGUMENTS`

Standards: `${CLAUDE_PLUGIN_ROOT}/references/stack/redhat-sso.md` (the mechanism) and
`${CLAUDE_PLUGIN_ROOT}/references/standards/security-baseline.md` (the rules).
Realm, client naming, and audience convention:
`${CLAUDE_PLUGIN_ROOT}/references/org-profile.md`.

**All authentication goes through Red Hat SSO.** No local user tables, no shared API
keys, no service-specific JWT signing. If a case appears not to fit, that is an ADR,
not a workaround — say so rather than building the exception.

## 1. Identify every caller

Not just the obvious one. For each: is it a browser, a backend acting for a user, a
backend acting as itself, or a scheduled job?

| Caller | Client type | Flow |
| --- | --- | --- |
| Browser app / SPA | Public | Authorization Code **with PKCE** |
| Backend acting for a user | Confidential | Receives and validates the user's token |
| Backend acting as itself | Confidential | Client credentials, service account |
| Scheduled job | Confidential | Client credentials |

**The case most often got wrong:** a backend calling a downstream service on a user's
behalf. Passing its own service-account token throws away the user's identity — the
downstream service can no longer enforce per-user authorization, and the audit trail
stops there. Pass the user's token, or use token exchange if the audience must change.
If a service account genuinely is correct here, that is a decision to state, not a
default to fall into.

## 2. Confirm the validation the service performs

Every service validates every token itself: **signature, issuer, audience, expiry** —
all four, with JWKS cached and rotation honoured.

Audience is the one most often missing. A valid token minted for a different client is
not a valid token for this service, and signature-only validation accepts it. Check
the actual validation code rather than the configuration's intent.

## 3. Design the authorization model

Write the rule out in words: **who may do what to which resource, and where that is
enforced.** Include the negative cases — what a valid but unprivileged token cannot do.

- Realm roles for organization-wide capabilities; client roles for service-specific
  ones; groups to assign sets of roles to people. Keep the token small.
- **Scopes are not permissions.** A scope says what a client asked for.
- **Per-resource authorization is the service's job.** A role of `orders-reader` does
  not answer "may this user read *this* order". This is the most common real
  vulnerability in systems of this shape.
- Tenant scoping comes from a validated claim and is enforced in **one** place — a
  repository filter or query wrapper — never repeated by convention in every query, and
  never taken from a request parameter or header.

## 4. Draw the gateway/service line

The nginx edge gateway may reject anonymous traffic early. That is an optimization,
not the control — see `${CLAUDE_PLUGIN_ROOT}/references/stack/nginx-gateway.md`.

**The service must be safe when called directly**, because internal traffic can reach
it without traversing the edge and a routing mistake can bypass it. State explicitly
which checks are duplicated at both layers and which live only in the service. A
service that trusts a header the gateway set is one routing change away from
unauthenticated access.

## 5. Decision checkpoints

Use `AskUserQuestion` for:

- Public versus confidential client where a UI could be either
- Propagating the user's token downstream versus switching to a service account
- The authorization model — role-based, attribute-based, or resource-ownership
- Realm and client layout, when the service crosses an existing boundary
- Any exception to the SSO baseline

## 6. Output

Add an authentication and authorization section to the design document, or write
`docs/architecture/<slug>/auth.md`: the caller inventory with client type and flow, the
validation each service performs, the authorization rule in words including negative
cases, the tenant-scoping mechanism and where it is enforced, the gateway/service
split, and the behaviour when SSO is unavailable.

Record client-model and authorization-model decisions with `/architect:adr`.

## 7. The tests that must exist

Report these as required, not optional. A suite that only proves authorized users
succeed has tested nothing about authorization:

- No token → rejected
- Expired token → rejected
- Valid token, **wrong audience** → rejected
- Valid token, insufficient role → rejected
- Valid token, correct role, **another tenant's resource** → rejected

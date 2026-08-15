# REST API standards

Applies to every HTTP API another team can call, including internal ones. "Internal"
is not a reason to skip the contract — internal consumers break just as loudly.

## Contract first

The OpenAPI document is the contract, it is written before the implementation, and
**the implementation is generated from it**. It lives in the service repository and is
published to wherever `../org-profile.md` says. An API without a published contract
does not exist as far as other teams are concerned.

The build rules — codegen, generated-code handling, spec linting, breaking-change
detection, and conformance testing in CI — are in `api-contract-first.md` and apply to
every API in this standard.

## Resources and URLs

- Nouns, plural, kebab-case: `/orders`, `/shipping-addresses`.
- Hierarchy only where the child cannot exist without the parent:
  `/orders/{orderId}/lines/{lineId}`. Beyond two levels, reconsider.
- No verbs in paths. The exception is a genuine action that is not a resource
  mutation — `POST /orders/{id}/cancel` is acceptable and better than contorting the
  resource model.
- Lower case, hyphens between words, no trailing slash, no file extensions.
- Query parameters for filtering, sorting, and pagination — never for identity.

## Methods and status codes

| Method | Semantics | Idempotent |
| --- | --- | --- |
| GET | Read, no side effects | Yes |
| POST | Create, or a non-idempotent action | No |
| PUT | Full replace at a known identity | Yes |
| PATCH | Partial update | Not inherently |
| DELETE | Remove | Yes |

- `200` read or update succeeded · `201` created, with `Location` · `202` accepted for
  async processing, with a way to check status · `204` success with no body.
- `400` malformed · `401` not authenticated · `403` authenticated but not permitted ·
  `404` not found *or* not permitted to know it exists · `409` conflict with current
  state · `412`/`428` precondition · `422` semantically invalid · `429` rate limited,
  with `Retry-After`.
- `500` we broke · `503` temporarily unavailable, with `Retry-After` · `504` upstream
  timeout.

**Never return 200 with an error in the body.** Every client's retry logic, every
proxy's caching, and every dashboard reads the status code.

## Idempotency

`POST` requests that create or charge accept an `Idempotency-Key` header. The server
stores the key with the response for a stated window and returns the original
response on replay. Without this, every client-side retry is a duplicate order.

`PUT` and `DELETE` are idempotent by definition — `DELETE` on an already-deleted
resource returns `204`, not `404`.

## Errors

One error shape across every service, per `errors.md`. Errors carry a stable machine
code, a human-readable message, and a correlation ID that appears in the logs and
traces.

## Pagination

Cursor-based by default:

```
GET /orders?limit=50&cursor=<opaque>
→ { "items": [...], "nextCursor": "<opaque>" }
```

Offset pagination is acceptable only for small, bounded collections. It degrades
badly at depth and produces duplicates and gaps when the underlying data changes
between pages. The cursor is opaque — clients must not decode it, and documenting
its structure guarantees they will.

Always set a default limit and a maximum limit. An unbounded list endpoint is a
denial-of-service vector against your own database.

## Filtering and sorting

- Explicit, documented parameters: `?status=open&sort=-createdAt`.
- Never accept a raw query fragment from the client. A `?filter=` that reaches the
  datastore is an injection vector and an unbounded-query vector at once.
- Every sortable and filterable field must be backed by an index.

## Versioning and compatibility

See `versioning.md`. Summary: major version in the path (`/v1/orders`), additive
changes only within a version, and a breaking change means a new major version
running alongside the old one for a stated deprecation period.

## Payloads

- JSON, `application/json`, UTF-8. `camelCase` field names, consistently.
- Timestamps are RFC 3339 in UTC with an explicit offset: `2026-08-15T09:30:00Z`.
- Money is an integer minor unit plus a currency code, never a float.
- Enums are strings, and clients must tolerate unknown values — adding an enum value
  is otherwise a breaking change.
- Nulls: prefer omitting an absent field to sending `null`, and be consistent.
- Never return internal identifiers, stack traces, or datastore field names.

## Security

Every endpoint authenticates, including health-adjacent ones that leak topology.
Authorization is checked per resource, not only per route — the classic failure is a
correctly authenticated user reading another tenant's order by ID. See
`security-baseline.md`.

## Operational contract

- Every endpoint documents its expected latency and its rate limit.
- Long-running work returns `202` with a status resource rather than holding a
  connection open.
- Bulk endpoints have a documented maximum batch size and return per-item results.
- `GET` responses set cache headers deliberately, even if the answer is `no-store`.

## Health endpoints

`/livez` and `/readyz` are distinct, unauthenticated within the cluster, excluded
from tracing, and never routed publicly. Readiness reflects dependency health;
liveness does not — see `../stack/openshift.md`.

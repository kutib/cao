# nginx edge gateway standards

nginx is the shared edge API gateway: one managed tier through which external traffic
reaches services. Hostnames, defaults, and who operates it are in `../org-profile.md`.

Inside the cluster, service-to-service traffic uses OpenShift Services directly — it
does not hairpin through the edge.

## What the gateway is responsible for

- **TLS termination** at the edge, with modern ciphers and auto-renewing certificates.
  Certificate expiry is one of the most common self-inflicted outages; it is alerted on
  well before the date.
- **Routing** to the right upstream service.
- **Request size limits** (`client_max_body_size`). An unbounded body is a
  denial-of-service vector, and the gateway is the cheapest place to stop it.
- **Rate limiting** per client identity, returning `429` with `Retry-After`.
- **Timeouts** — connect, send, and read — set explicitly.
- **Header hygiene** — strip inbound hop-by-hop and identity headers that clients must
  not be able to set, set `X-Forwarded-*` correctly, and never pass through a
  client-supplied `X-User-Id` or equivalent.
- **Early rejection** of anonymous traffic where a route requires authentication.
- **Access logging** with the correlation identifier.

## What must never be delegated to it

This is the more important half of the standard. Each of these has to live in the
service, because the gateway is not a trust boundary the service can rely on: internal
traffic can reach a service without traversing the edge, a routing mistake can bypass
it, and a compromised pod is already past it.

- **Token validation.** The gateway may check a token early. The service validates it
  again — signature, issuer, audience, expiry. See `redhat-sso.md`.
- **Per-resource authorization.** The gateway cannot know whether this user may read
  *this* order. It never sees the data.
- **Business validation.** Field-level rules belong with the code that owns the
  invariant.
- **Idempotency.** `Idempotency-Key` handling requires the state the service owns.
- **Tenant scoping.**

**A service must be safe when called directly.** Test it that way — the assumption that
"all traffic comes through the gateway" is the one that fails.

## Configuration baseline

Every route sets, explicitly:

- `proxy_connect_timeout`, `proxy_send_timeout`, `proxy_read_timeout` — aligned with
  the service's own budget. **The gateway timeout must be longer than the service's
  internal timeout**, or the client sees a gateway error while the service is still
  working and the real failure is invisible.
- `client_max_body_size` — the smallest value the route actually needs.
- `proxy_next_upstream` set deliberately. Retrying a non-idempotent `POST` at the
  gateway creates duplicates that the application never sees — see
  `../standards/api-rest.md`.
- Buffering settings appropriate to the payload. Streaming and long-lived connections
  (SSE, gRPC, websockets) need buffering off and keepalives aligned, or they die
  silently at the proxy.

Configuration is version-controlled and reviewed. A route added by hand on the gateway
host is a route nobody can reproduce or roll back.

## Correlation and observability

- Generate `X-Request-Id` when absent and pass it through; the service uses it as the
  `correlationId` returned in errors. See `../standards/errors.md`.
- **Propagate W3C `traceparent` unchanged.** A gateway that drops or regenerates trace
  context severs every trace at the edge, which is exactly where you most need it. See
  `opentelemetry.md`.
- Gateway access logs and service logs must be joinable on the same identifier, or an
  incident becomes two separate investigations.
- Export gateway metrics per route — request rate, status classes, upstream latency,
  and rejections by reason. Gateway latency minus upstream latency is where queueing
  and TLS cost show up.

## Failure modes to design for

- **The gateway is a single shared dependency.** Its outage is everyone's outage. It
  runs with redundancy and a PodDisruptionBudget, and a config reload must not drop
  connections.
- **A bad config reload** takes down every service at once. Validate configuration
  before applying, and roll out gateway changes as deliberately as application
  changes.
- **Upstream unavailable** — the gateway returns `502`/`503`, which the client sees
  instead of your error shape. Whatever the client-facing error contract is for this
  case, it must be stated rather than discovered.
- **Timeout mismatch** — client gives up before the gateway, or the gateway before the
  service. Work the whole chain out once and write the numbers down.
- **Rate limiting is shared state.** Understand whether the limit is per gateway
  instance or global, because per-instance limits multiply by replica count.

## In the design document

Every externally reachable service states: its routes, the size and rate limits on
each, the timeout chain from client through gateway to service, which routes require
authentication, and what the client sees when the gateway cannot reach it.

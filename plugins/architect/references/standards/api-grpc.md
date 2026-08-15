# gRPC standards

Use gRPC for internal service-to-service calls where the contract is stable, the
latency budget is tight, or streaming is genuinely needed. Externally facing APIs use
REST unless there is a specific reason not to — see `api-rest.md`.

## Package and naming

- Package includes the major version: `orders.v1`. A breaking change means
  `orders.v2` alongside it, not an edit.
- Services are named for the capability: `OrderService`. RPCs are verbs:
  `PlaceOrder`, `GetOrder`, `ListOrders`.
- Every RPC takes a dedicated request message and returns a dedicated response
  message, even when one field would do. `GetOrderRequest` can gain a field;
  `string` cannot.

## Proto hygiene

- `proto3`, one service per file where practical, imports explicit.
- **Never reuse a field number.** Reserve removed numbers and names:
  `reserved 4, 7; reserved "legacyStatus";`. Reusing a number silently reinterprets
  old bytes as a new field — the wire format has no idea a rename happened.
- Field numbers 1–15 use one byte; give them to the fields present on every message.
- Enums have a zero value meaning "unspecified": `ORDER_STATUS_UNSPECIFIED = 0`.
  Proto3 cannot distinguish an unset enum from the zero value, so making the zero
  value meaningful guarantees a bug.
- Prefix enum values with the enum name — proto enum values share a C++ scope.
- `google.protobuf.Timestamp` for time, never a bare int64 with an assumed unit.
- Money is an integer minor unit plus a currency string, never a float or a double.

## Compatibility

Wire-compatible: adding a field, adding an RPC, adding an enum value, renaming a
field (the name is not on the wire — but it *is* in generated code, so this breaks
callers at compile time).

Breaking: changing a field number, changing a field type, changing cardinality,
removing an RPC, moving a field into or out of a `oneof`, and changing the semantics
of anything.

See `versioning.md` for the deprecation process, which applies unchanged.

## Errors

Use the standard status codes and mean them:

| Code | Use for |
| --- | --- |
| `INVALID_ARGUMENT` | Malformed request, independent of state |
| `FAILED_PRECONDITION` | Well-formed but wrong for the current state |
| `NOT_FOUND` | Missing, or not permitted to know it exists |
| `ALREADY_EXISTS` | Idempotent-create conflict |
| `PERMISSION_DENIED` | Authenticated, not authorized |
| `UNAUTHENTICATED` | No valid credential |
| `RESOURCE_EXHAUSTED` | Rate or quota limit |
| `UNAVAILABLE` | Transient — the only code clients should retry by default |
| `DEADLINE_EXCEEDED` | Timed out |
| `INTERNAL` | Our defect |

The distinction between `INVALID_ARGUMENT` and `FAILED_PRECONDITION` decides whether
a retry can ever succeed. Getting it wrong produces clients that retry forever or
give up too early.

Attach details with `google.rpc.ErrorInfo` and `BadRequest`, carrying the same
stable `code` and `correlationId` as the REST error shape in `errors.md`.

## Deadlines and retries

- **Every call sets a deadline.** A gRPC call without one waits forever, and the
  default in most clients is exactly that.
- Deadlines propagate: a server passes its remaining budget to its own downstream
  calls rather than starting a fresh one. Without propagation, a chain of three
  services each allowing 5 seconds can take 15.
- Retry only `UNAVAILABLE` and `DEADLINE_EXCEEDED` on idempotent RPCs, with backoff
  and jitter and a bounded budget. Configure this in the service config rather than
  hand-rolling it per call site.

## Streaming

Use streaming for genuinely continuous data, not to avoid pagination.

- Server streaming for large result sets and change feeds.
- Client streaming for bulk ingest.
- Bidirectional streaming rarely; it is the hardest to reason about and to operate.
- Every stream needs a flow-control story: what happens when the consumer is slower
  than the producer. Unbounded buffering is the default failure and it is an OOM.
- Long-lived streams need keepalive settings that match the ingress and proxy
  timeouts in `../stack/openshift.md`, or they die silently at the infrastructure
  layer.

## Operating on OpenShift

- gRPC is HTTP/2 and long-lived: a Kubernetes Service load-balances connections, not
  requests, so one client connection pins to one pod. Use client-side load balancing
  with the headless service, or a proxy that understands gRPC, or scaling the server
  will not spread the load.
- Health checking uses the standard gRPC health protocol, wired to the readiness
  probe.
- Instrument with the OTel gRPC interceptors; trace context travels in metadata —
  `../stack/opentelemetry.md`.
- mTLS between services per `security-baseline.md`. Reflection is disabled in
  production.

# OpenShift standards

Cluster, registry, and namespace conventions live in `../org-profile.md`.

## Workload shape

- **Deployment** for stateless services. **StatefulSet** only when stable identity or
  per-replica storage is genuinely required — most services that reach for one do not
  need it. **CronJob** for scheduled work, with `concurrencyPolicy` set deliberately
  and `startingDeadlineSeconds` bounded.
- Every workload declares **resource requests and limits**. Requests are what the
  scheduler reserves; limits are what the kernel enforces.
  - Set requests from observed usage, not from guesses.
  - CPU limits cause throttling that looks like mysterious latency. Consider omitting
    the CPU limit while always setting the request; always set a memory limit,
    because the alternative to an OOMKill is a node under memory pressure.
  - A pod without requests lands in BestEffort QoS and is evicted first.
- **Probes are three different questions.** Do not point them all at the same handler:
  - *Startup*: has it finished booting? Generous failure threshold.
  - *Readiness*: can it serve traffic right now? Fails when a critical dependency is
    down, which removes the pod from the Service.
  - *Liveness*: is it wedged and only a restart will fix it? Should almost never fail.
    A liveness probe that checks a downstream dependency turns that dependency's
    outage into a restart loop across the whole fleet.
- **PodDisruptionBudget** for anything taking traffic, or a node drain takes the
  service down.
- **`terminationGracePeriodSeconds`** long enough for in-flight work to drain, and the
  application must handle SIGTERM: stop accepting new work, finish what it has, exit.
  Add a small pre-stop delay so the endpoint is removed from load balancers before
  the process stops accepting connections.
- **Replicas ≥ 2** for any service with an availability target, spread across nodes
  with anti-affinity or topology spread constraints.

## Containers

- Base images come from the internal registry and the approved list.
- **Run as non-root.** OpenShift assigns an arbitrary UID by default: the image must
  not assume a fixed UID, and any writable directory must be group-writable by root
  group (GID 0).
- `readOnlyRootFilesystem: true` with explicit `emptyDir` volumes for scratch space.
- `allowPrivilegeEscalation: false`, all capabilities dropped, no privileged
  containers. A workload needing more is an exception requiring security sign-off.
- Images are tagged with an immutable version or digest. `latest` in production means
  no one knows what is running.
- Images are scanned; critical findings block promotion.

## Configuration and secrets

- Non-sensitive configuration in ConfigMaps, injected as environment variables or
  mounted files.
- **Secrets never live in git.** Use the org's sealed-secret or vault mechanism from
  `../org-profile.md`. A Kubernetes Secret is base64, not encryption — treat its
  contents as readable by anyone with namespace access.
- Configuration changes should not require an image rebuild; a rolling restart is
  acceptable and expected.

## Networking

- **NetworkPolicy default deny**, with explicit allows for the traffic that should
  exist. Without a policy, every pod in the cluster can reach every other pod.
- **External traffic arrives through the shared nginx edge gateway** — see
  `nginx-gateway.md`. In-cluster service-to-service traffic goes directly through
  Services and does not hairpin through the edge.
- Routes terminate TLS; internal service-to-service traffic uses TLS or mTLS per
  `../standards/security-baseline.md`.
- **External datastores are egress dependencies.** Oracle lives outside the cluster, so
  it needs an egress rule, a connect timeout, a statement timeout, and a defined
  behaviour when unreachable — see `oracle.md`.
- Service names are stable and namespaced; do not hardcode pod IPs or rely on
  ordering.

## Scaling

- HorizontalPodAutoscaler on a metric that reflects the actual bottleneck. CPU is the
  default and is often wrong — a consumer bound by broker throughput does not respond
  to CPU. Custom metrics (queue depth, consumer lag) usually correlate better.
- Set `minReplicas` at or above the availability floor and `maxReplicas` below what
  the downstream datastore can survive. **Autoscaling a service is autoscaling load
  onto its dependencies**; the database connection limit is the usual casualty.
- **With Oracle the arithmetic is explicit and shared**: `pool size × maxReplicas` must
  stay within the service's allocated share of the instance's `processes` limit.
  Exceeding it takes down every other service on that instance, not just yours — see
  `oracle.md`.
- Kafka consumer replicas above the partition count idle — cap accordingly.

## Deploys and rollback

- Rolling updates with `maxUnavailable: 0` for services that cannot drop requests.
- Rollback is tested from the actual deployed version, not assumed.
- A database migration that is not backwards compatible with the previous application
  version makes rollback impossible. Expand-and-contract: add the new shape, deploy
  code that writes both, migrate, then remove the old shape in a later release.

## Observability wiring

- Every workload sets the standard resource attributes for OpenTelemetry —
  `service.name`, `service.version`, `deployment.environment`, namespace, pod — see
  `opentelemetry.md`.
- Logs go to stdout as structured JSON. Applications do not write log files inside
  containers.
- Metrics are exposed for scraping or pushed to the collector, per
  `../org-profile.md`.

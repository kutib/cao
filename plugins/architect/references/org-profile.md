# Organization profile

**This is the only file in the plugin with organization-specific values.** Everything
else is generic standard. The platform team fills this in once and keeps it current;
every other reference and skill defers to it.

Values marked `TODO` have not been set yet. When a skill needs one and finds `TODO`,
it must ask the developer rather than inventing a value.

## Platform

| Setting | Value |
| --- | --- |
| OpenShift version | `TODO` |
| Cluster tiers | `TODO` (e.g. dev / staging / prod) |
| Namespace convention | `TODO` (e.g. `<team>-<service>-<env>`) |
| Internal image registry | `TODO` (e.g. `registry.internal.example.com`) |
| Approved base images | `TODO` (e.g. `ubi9/openjdk-21`, `ubi9/nodejs-22`) |
| Ingress domain | `TODO` |
| Service mesh in use | `TODO` (yes/no; if yes, which) |
| Secret management | `TODO` (e.g. Sealed Secrets, Vault, External Secrets Operator) |

## Edge gateway (nginx)

| Setting | Value |
| --- | --- |
| Gateway hostnames | `TODO` |
| Who operates it | `TODO` (team, and how a route change is requested) |
| Default timeouts | `TODO` (connect / send / read) |
| Default `client_max_body_size` | `TODO` |
| Default rate limit | `TODO` (and whether it is per-instance or global) |
| Where route config lives | `TODO` (repository and review process) |

## Datastores

| Setting | Value |
| --- | --- |
| Oracle instances | `TODO` (version, RAC/Data Guard, per environment) |
| Oracle `processes` / `sessions` limit | `TODO` — **the number connection pools are budgeted against** |
| Per-service connection budget | `TODO` (pool size × max replicas must stay under it) |
| Oracle access model | `TODO` (per-service schema and credentials) |
| Migration tool | `TODO` (Liquibase or Flyway) |
| MongoDB deployment | `TODO` (replica set size, sharded or not, version) |
| MongoDB access | `TODO` (per-service user? shared cluster? dedicated?) |
| Elasticsearch cluster | `TODO` (node count, version, hot/warm tiers) |
| Elasticsearch access | `TODO` |
| Default backup schedule and retention | `TODO` |

## Messaging

| Setting | Value |
| --- | --- |
| Kafka cluster(s) | `TODO` (brokers, version, rack awareness) |
| Kafka default replication factor | `TODO` (3 recommended) |
| Kafka `min.insync.replicas` | `TODO` (2 recommended with RF 3) |
| Schema registry | `TODO` (URL, or "none — schemas live in the contract repo") |
| Topic naming convention | `TODO` (e.g. `<domain>.<entity>.<event>.v<major>`) |
| RabbitMQ cluster | `TODO` (nodes, version, quorum queues available?) |
| Queue naming convention | `TODO` |

## Identity and access — Red Hat SSO

| Setting | Value |
| --- | --- |
| Product and version | `TODO` (RH-SSO 7.x, or Red Hat build of Keycloak) |
| Base URL per environment | `TODO` |
| Realm layout | `TODO` (one realm, or per domain / environment) |
| Client naming convention | `TODO` |
| Token audience convention | `TODO` |
| Role and group naming | `TODO` |
| Service-to-service auth | `TODO` (client credentials / mTLS / both) |
| Access token lifetime | `TODO` (minutes) |
| Where client secrets live | `TODO` (secret store, and rotation cadence) |

## CI and code quality

| Setting | Value |
| --- | --- |
| SonarQube server | `TODO` |
| Quality gate name | `TODO` |
| Coverage threshold on new code | `TODO` (80% suggested) |
| Standard coverage exclusions | `TODO` (generated code paths) |
| Contract linting | `TODO` (e.g. Spectral ruleset location) |
| Breaking-change detection | `TODO` (e.g. oasdiff, buf) |
| Where API specs are published | `TODO` |
| Minimum deprecation window | `TODO` |

## AI features

| Setting | Value |
| --- | --- |
| Model gateway endpoint | `TODO` |
| Available models | `TODO` (Claude Opus 5 default; Haiku 4.5 / Sonnet 5 where suitable) |
| How services authenticate to the gateway | `TODO` |
| Prompt / completion retention at the gateway | `TODO` |
| Per-team cost limits | `TODO` |
| Where eval sets live and how CI runs them | `TODO` |
| MCP server registry | `TODO` |

## Observability

| Setting | Value |
| --- | --- |
| OTel collector endpoint | `TODO` |
| Trace backend | `TODO` (e.g. Jaeger, Tempo) |
| Metric backend | `TODO` (e.g. Prometheus, Thanos) |
| Log backend | `TODO` (e.g. Elasticsearch + Kibana, Loki) |
| Dashboard tool and folder convention | `TODO` |
| Alert routing | `TODO` (e.g. Alertmanager → PagerDuty) |
| Default trace sampling | `TODO` (e.g. 10% head, 100% of errors) |

## Default SLO targets

Starting points, not ceilings. A service negotiates its real targets with its
consumers; these apply when nobody has negotiated anything.

| Tier | Availability | Latency p95 | Latency p99 |
| --- | --- | --- | --- |
| Tier 1 — user-facing critical | `TODO` (99.9% suggested) | `TODO` (300 ms) | `TODO` (1 s) |
| Tier 2 — user-facing non-critical | `TODO` (99.5%) | `TODO` (800 ms) | `TODO` (2 s) |
| Tier 3 — internal / batch | `TODO` (99.0%) | best effort | best effort |

## Documentation and knowledge base (Confluence)

| Setting | Value |
| --- | --- |
| Confluence base URL | `TODO` |
| MCP server connected | `TODO` (which one — tool names differ between them) |
| Architecture space | `TODO` (key and name) |
| Standards space | `TODO` |
| Runbook / post-incident space | `TODO` |
| Page naming convention | `TODO` |
| Labels to apply | `TODO` (e.g. `architecture`, `hld`, `<service-name>`) |
| **Design document home** | `repo` *(default until set — see below)* |

**Design document home** decides where `/architect:design` and
`/architect:detail-design` write. Set it to one of:

- `repo` — design documents live in `docs/architecture/`. Confluence is read for prior
  art only. **This is the default until the Architecture Office sets it**, because it
  requires no permissions and cannot publish anything by accident.
- `confluence` — design documents are published as Confluence pages in the
  architecture space, and the repository holds a link.

**ADRs always live in the repository** (`docs/adr/`), regardless of this setting. They
version with the code they constrain and appear in the diff a reviewer reads. See
`stack/confluence-mcp.md`.

## Governance

| Setting | Value |
| --- | --- |
| Architecture Office contact | `TODO` |
| ADR location in a repo | `docs/adr/` |
| Design document location | per **Design document home** above |
| Where to propose a standards change | `TODO` (PR against the `cao` repo) |
| Readiness review required before | first production deploy of a new service |

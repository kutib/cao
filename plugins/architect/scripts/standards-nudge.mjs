// PreToolUse (Write|Edit|NotebookEdit): when a governed artifact is about to be
// written, put the governing standard in front of Claude.
//
// This hook is advisory by contract. It never returns a permission decision — the
// architect informs the change, it does not veto it.

import { run, normalize, readState, writeState, pluginFile } from "./lib.mjs";

const CATEGORIES = [
  {
    id: "api-contract",
    label: "public API contract",
    re: /(^|\/)(openapi|swagger)[.\w-]*\.(ya?ml|json)$|(^|\/)asyncapi[.\w-]*\.ya?ml$|\.proto$/i,
    refs: [
      "references/standards/api-contract-first.md",
      "references/standards/api-rest.md",
      "references/standards/versioning.md",
      "references/standards/errors.md",
    ],
    note: "The spec is the build's source of truth: the implementation is generated from it and CI proves the two match. Contract changes are visible to other teams — check compatibility before saving.",
  },
  {
    id: "schema-migration",
    label: "database schema or migration",
    re: /(^|\/)(migrations?|changelogs?)\/|(^|\/)db\.changelog[\w.-]*\.(xml|ya?ml|json|sql)$|\.sql$/i,
    refs: [
      "references/stack/oracle.md",
      "references/stack/mongodb.md",
      "references/standards/versioning.md",
    ],
    note: "Every migration must be readable by the previous application version, or rollback becomes impossible. Expand and contract; run migrations as a job, never on startup. On Oracle: bind variables, never string-concatenated literals.",
  },
  {
    id: "nginx-config",
    label: "gateway configuration",
    re: /(^|\/)nginx[\w.-]*\.conf$|(^|\/)nginx\/|(^|\/)conf\.d\/[\w.-]+\.conf$/i,
    refs: ["references/stack/nginx-gateway.md"],
    note: "The gateway handles TLS, routing, rate limits, size limits, and timeouts. It never handles per-resource authorization, business validation, or idempotency — and the service must be safe when called directly.",
  },
  {
    id: "sonar-config",
    label: "Sonar quality-gate configuration",
    re: /(^|\/)sonar-project\.properties$|(^|\/)\.sonarcloud\.properties$/i,
    refs: ["references/standards/testing-and-coverage.md"],
    note: "Generated code must be excluded or the gate is unwinnable. Excluding error handling, retries, or authorization is gaming it — every exclusion needs a stated reason.",
  },
  {
    id: "ai-prompt",
    label: "prompt or model configuration",
    re: /(^|\/)prompts?\/|[\w.-]*\.prompt(\.[\w]+)?$|(^|\/)[\w.-]*system[_-]?prompt[\w.-]*\.(md|txt|ya?ml|json)$/i,
    refs: [
      "references/standards/ai-engineering.md",
      "references/standards/data-classification.md",
    ],
    note: "No secrets in prompts — they reach transcripts, logs, and traces. Treat anything the model reads as untrusted, and remember a prompt change re-triggers the feature's evals.",
  },
  {
    id: "mcp-config",
    label: "MCP tool surface",
    re: /(^|\/)\.mcp\.json$|(^|\/)mcp[\w.-]*\.json$/i,
    refs: ["references/stack/mcp-servers.md", "references/standards/ai-engineering.md"],
    note: "The tool surface is a contract with a non-deterministic client. Tools authorize as the calling user, not the server; destructive tools need confirmation; a description change alters tool selection and re-triggers evals.",
  },
  {
    id: "openshift-manifest",
    label: "OpenShift workload manifest",
    re: /(^|\/)(deployment|deploymentconfig|statefulset|service|route|ingress|hpa|networkpolicy|poddisruptionbudget|cronjob)[.\w-]*\.ya?ml$|(^|\/)(Chart\.ya?ml|values[.\w-]*\.ya?ml|kustomization\.ya?ml)$|\.tpl$/i,
    refs: ["references/stack/openshift.md"],
    note: "Every workload needs resource requests and limits, probes, a non-root securityContext, and a PodDisruptionBudget if it takes traffic.",
  },
  {
    id: "container-image",
    label: "container image definition",
    re: /(^|\/)(Dockerfile|Containerfile)[.\w-]*$/i,
    refs: ["references/stack/openshift.md"],
    note: "Images run non-root with an arbitrary UID on OpenShift. Base image must come from the internal registry.",
  },
  {
    id: "messaging",
    label: "messaging topology",
    re: /(^|\/)[\w.-]*(kafka|rabbit|amqp|topics?|queues?|consumer|producer|binder|streams)[\w.-]*\.(ya?ml|json|properties|conf|toml)$/i,
    refs: [
      "references/stack/messaging-choice.md",
      "references/stack/kafka.md",
      "references/stack/rabbitmq.md",
      "references/standards/api-async-events.md",
    ],
    note: "A new topic or queue is a public contract. Partitioning, retention, keying, consumer-group naming, and the DLQ path all need explicit answers.",
  },
  {
    id: "datastore-index",
    label: "index or mapping definition",
    re: /(^|\/)(mappings?|indices|indexes)\//i,
    refs: [
      "references/stack/elasticsearch.md",
      "references/stack/mongodb.md",
      "references/stack/oracle.md",
    ],
    note: "Index and mapping changes are hard to reverse in production. Confirm the query patterns they serve and the rollout order. Every index is justified by a named query.",
  },
  {
    id: "telemetry-config",
    label: "telemetry configuration",
    re: /(^|\/)[\w.-]*(otel|opentelemetry|collector|tracing|telemetry)[\w.-]*\.(ya?ml|json|properties|toml)$/i,
    refs: [
      "references/stack/opentelemetry.md",
      "references/standards/metrics-naming.md",
      "references/standards/logging.md",
    ],
    note: "Resource attributes, sampling, and metric naming must match the org convention or dashboards and alerts will not correlate.",
  },
  {
    id: "secret-material",
    label: "credential or secret material",
    re: /(^|\/)(secret|secrets)[.\w-]*\.ya?ml$|(^|\/)\.env(\.|$)|(^|\/)credentials?[.\w-]*\.(ya?ml|json|properties)$/i,
    refs: ["references/standards/security-baseline.md"],
    note: "No plaintext secrets in git. Reference the sealed-secret or vault path instead of the value.",
  },
];

const DECISION_RECORD = /(^|\/)docs\/(adr|architecture)\//i;

run((input) => {
  const toolInput = input.tool_input || {};
  const path = normalize(
    toolInput.file_path || toolInput.notebook_path || toolInput.path || "",
  );
  if (!path) return {};

  const state = readState(input.session_id);

  if (DECISION_RECORD.test(path)) {
    // A decision is being recorded. Remember it so the Stop gate stays quiet.
    writeState(input.session_id, { ...state, recorded: true, touched: state.touched });
    return {};
  }

  const hit = CATEGORIES.find((c) => c.re.test(path));
  if (!hit) return {};

  const touched = state.touched.includes(hit.id)
    ? state.touched
    : [...state.touched, hit.id];
  const alreadyNudged = state.touched.includes(hit.id);
  writeState(input.session_id, { ...state, touched });

  // Say it once per category per session. Repeating it on every file edit is noise.
  if (alreadyNudged) return {};

  const refs = hit.refs.map((r) => `- \`${pluginFile(r)}\``).join("\n");

  return {
    additionalContext: [
      `Architecture governance: you are editing a ${hit.label} (\`${path}\`).`,
      "",
      hit.note,
      "",
      "Governing standards — read the relevant one if this change is more than cosmetic:",
      refs,
    ].join("\n"),
  };
});

// UserPromptSubmit: two jobs.
//
// 1. Deliver the standing charter once per session, if SessionStart did not manage
//    to. This is the reliable delivery path — plugin SessionStart hooks do not fire
//    in every mode. Landing the charter on the first prompt is early enough: it is
//    in context before any work begins.
// 2. Route architecture-shaped requests to the right skill. Pure regex, no model
//    call. Precision beats recall — a wrong nudge on every prompt trains developers
//    to ignore the architect.

import { run, readState, writeState } from "./lib.mjs";
import { buildCharter } from "./charter.mjs";

const RULES = [
  {
    skill: "/architect:design",
    why: "this introduces or reshapes a system boundary",
    re: /\b(new (micro)?service|new component|new module|greenfield|from scratch|high[- ]level design|system design|architect(ure)?|hld|c4 (model|diagram)|break (this )?(up|apart)|split (the )?(service|monolith)|extract a service|nginx|api gateway|ingress|edge gateway)\b/i,
  },
  {
    skill: "/architect:detail-design",
    why: "this needs component-level design before implementation",
    re: /\b(low[- ]level design|lld|detailed design|sequence diagram|class diagram|data model|schema design|internal design|migration script|liquibase|flyway|pl\/?sql|stored procedure)\b/i,
  },
  {
    skill: "/architect:api-design",
    why: "this defines or changes a contract other teams depend on",
    re: /\b(api|endpoint|openapi|swagger|asyncapi|rest|grpc|protobuf|\.proto|contract|payload|request\/response|versioning|breaking change|pagination|codegen|code ?generat|generated client|spectral)\b/i,
  },
  {
    skill: "/architect:tech-select",
    why: "this is a technology choice that needs a recorded decision",
    re: /\b(kafka|rabbitmq|rabbit mq|mongo(db)?|oracle|elastic(search)?|which (database|datastore|broker|queue|technology)|should (i|we) use|redis|cache layer|message broker|event bus)\b/i,
  },
  {
    skill: "/architect:auth-design",
    why: "authentication and authorization go through Red Hat SSO",
    re: /\b(keycloak|red ?hat sso|rh-?sso|oidc|openid|realm|client credentials|service account|access token|refresh token|token validation|single sign|login flow|pkce)\b/i,
  },
  {
    skill: "/architect:ai-feature",
    why: "a model in the path brings failure and attack surfaces ordinary services do not have",
    re: /\b(llm|large language model|claude|gpt|prompt|prompting|embedding|vector (db|database|store|search)|rag|retrieval[- ]augmented|ai (feature|agent|assistant)|agentic|semantic search|fine[- ]tun|hallucinat)\b/i,
  },
  {
    skill: "/architect:mcp-design",
    why: "exposing a capability as a tool for a model is a public contract with a non-deterministic client",
    re: /\b(mcp|model context protocol|tool server|expose .{0,20}as a tool|tool definition|tool schema)\b/i,
  },
  {
    skill: "/architect:test-strategy",
    why: "the Sonar quality gate needs to be satisfied honestly",
    re: /\b(sonar(qube)?|quality gate|code coverage|coverage (gate|threshold|report|is (low|failing))|test strategy|what should (i|we) test|flaky test|security hotspot|testcontainers)\b/i,
  },
  {
    skill: "/architect:separation-of-concerns",
    why: "this touches module boundaries and dependency direction",
    re: /\b(coupling|cohesion|boundar(y|ies)|layering|dependency (direction|inversion)|domain model|bounded context|anti[- ]corruption|shared (library|module)|circular dependency)\b/i,
  },
  {
    skill: "/architect:threat-model",
    why: "this has a security surface that should be modelled, not assumed",
    re: /\b(auth[nz]?|authenticat|authoriz|oauth|oidc|jwt|token|secret|credential|password|encrypt|tls|mtls|rbac|permission|pii|gdpr|vulnerab|threat|network ?policy)\b/i,
  },
  {
    skill: "/architect:scale-plan",
    why: "this has capacity and sizing consequences",
    re: /\b(scal(e|ing|ability)|throughput|capacity|sizing|shard|partition|replica|load test|benchmark|rps|qps|hpa|autoscal|hot ?spot|backpressure)\b/i,
  },
  {
    skill: "/architect:observability-plan",
    why: "instrumentation should be designed with the change, not bolted on",
    re: /\b(observability|opentelemetry|otel|tracing|trace|span|instrument(ation)?|correlation id|structured log|log aggregation)\b/i,
  },
  {
    skill: "/architect:metrics-strategy",
    why: "metrics and alerts need to map to symptoms, not internals",
    re: /\b(metric|slo|sli|sla|error budget|alert(ing)?|dashboard|prometheus|grafana|p9[59]|percentile|golden signal)\b/i,
  },
  {
    skill: "/architect:reliability-review",
    why: "this needs an explicit answer for how it fails",
    re: /\b(reliab|resilien|retry|retries|backoff|idempoten|circuit breaker|dead[- ]letter|dlq|timeout|failover|disaster recovery|graceful (degradation|shutdown)|at[- ]least[- ]once|exactly[- ]once|outage)\b/i,
  },
  {
    skill: "/architect:readiness",
    why: "a first production deploy has a gate to clear",
    re: /\b(deploy to prod(uction)?|go[- ]live|production ready|readiness (review|check)|launch checklist|cut ?over)\b/i,
  },
  {
    skill: "/architect:arch-review",
    why: "a review should be checked against the architecture standards",
    re: /\b(review (this|my|the) (pr|change|diff|branch|design)|architecture review|design review|is this (design|approach) (ok|right|sound))\b/i,
  },
];

run((input) => {
  const prompt = String(input.prompt || "");
  const state = readState(input.session_id);
  const sections = [];
  const next = { ...state };

  // 1. The charter, once per session.
  if (!state.charterSent) {
    sections.push(buildCharter(input.cwd));
    next.charterSent = true;
  }

  // 2. Routing, for prompts long enough to classify.
  if (prompt.length >= 12) {
    const seen = new Set(state.notified);
    const matched = RULES.filter((r) => r.re.test(prompt) && !seen.has(r.skill));

    // Cap the nudge. Suggesting six skills at once is the same as suggesting none.
    const picked = matched.slice(0, 3);
    if (picked.length > 0) {
      for (const rule of picked) seen.add(rule.skill);
      next.notified = [...seen];

      sections.push(
        [
          "Architecture governance: this request looks like it touches the areas below.",
          "Invoke the matching skill before designing or implementing, and use its decision checkpoints rather than choosing silently.",
          "",
          picked.map((r) => `- \`${r.skill}\` — ${r.why}`).join("\n"),
          "",
          "If the request turns out not to need them, say so in one line and continue.",
        ].join("\n"),
      );
    }
  }

  if (sections.length === 0) return {};

  writeState(input.session_id, next);
  return { additionalContext: sections.join("\n\n---\n\n") };
});

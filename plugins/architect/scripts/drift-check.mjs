// Stop: the soft gate.
//
// If a turn changed something architecturally consequential and nothing was
// recorded in docs/adr/ or docs/architecture/, say so once. This is a reminder
// delivered to the developer, not a block — the turn has already ended.

import { run, readState, writeState } from "./lib.mjs";

const GOVERNED = {
  "api-contract": "a public API contract",
  messaging: "messaging topology (a topic, queue, or consumer group)",
  "schema-migration": "a database schema or migration",
  "datastore-index": "a datastore index or mapping",
  "mcp-config": "an MCP tool surface",
  "openshift-manifest": "an OpenShift workload manifest",
};

run((input) => {
  const state = readState(input.session_id);

  // Already reminded once this session, or the decision was recorded. Stay quiet.
  if (state.gated || state.recorded) return {};

  const governed = state.touched.filter((id) => id in GOVERNED);
  if (governed.length === 0) return {};

  writeState(input.session_id, { ...state, gated: true });

  const what = governed.map((id) => GOVERNED[id]);
  const list =
    what.length === 1
      ? what[0]
      : `${what.slice(0, -1).join(", ")} and ${what[what.length - 1]}`;

  return {
    systemMessage: [
      `Architecture governance: this session changed ${list}, and nothing was written to docs/adr/ or docs/architecture/.`,
      "",
      "If a decision was made here that a future reader would need to understand, record it with /architect:adr.",
      "If the change was mechanical, no action is needed — this reminder appears once per session.",
    ].join("\n"),
  };
});

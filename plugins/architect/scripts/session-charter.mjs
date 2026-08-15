// SessionStart: inject the standing architecture charter as early as possible.
//
// This is the earliest delivery point, but it is not a reliable one — plugin
// SessionStart hooks do not fire in every mode, and SessionStart's
// additionalContext is dropped in non-interactive (-p) sessions. route.mjs
// delivers the charter on the first user prompt when this hook did not manage to.
// Whichever runs first sets `charterSent`, so it is never injected twice.

import { run, readState, writeState } from "./lib.mjs";
import { buildCharter } from "./charter.mjs";

run((input) => {
  const state = readState(input.session_id);
  if (state.charterSent) return {};

  writeState(input.session_id, { ...state, charterSent: true });
  return { additionalContext: buildCharter(input.cwd) };
});

// Shared helpers for the architect plugin's hooks.
// Every hook must fail soft: a broken architect hook never blocks a developer.

import {
  readFileSync,
  writeFileSync,
  mkdirSync,
  readdirSync,
  statSync,
  rmSync,
} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";

/**
 * Absolute path to the plugin's installation directory.
 * `${CLAUDE_PLUGIN_ROOT}` is substituted in hook *commands*, not in hook output,
 * so anything we hand back to Claude has to resolve the path itself. This module
 * lives in `<plugin root>/scripts/`.
 */
export const PLUGIN_ROOT = dirname(dirname(fileURLToPath(import.meta.url)));

/** Absolute path to a file bundled with the plugin, in forward-slash form. */
export function pluginFile(relative) {
  return join(PLUGIN_ROOT, relative).replace(/\\/g, "/");
}

/** Read the hook's JSON payload from stdin. Returns {} if anything goes wrong. */
export function readInput() {
  try {
    const raw = readFileSync(0, "utf8");
    return raw.trim() ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/** Emit a hook result and exit 0. Emitting nothing is a valid "no opinion". */
export function emit(output) {
  if (output && Object.keys(output).length > 0) {
    process.stdout.write(JSON.stringify(output));
  }
  process.exit(0);
}

/**
 * Run a hook body, swallowing every error. On failure we exit 0 with no output
 * rather than a non-zero code, so nothing lands in the user's error tab for
 * what is only advisory context.
 */
export function run(fn) {
  try {
    const result = fn(readInput());
    emit(result || {});
  } catch {
    emit({});
  }
}

/** Normalize a path to forward slashes so the same patterns work on Windows. */
export function normalize(p) {
  return String(p || "").replace(/\\/g, "/");
}

// --- per-session scratch state -------------------------------------------------
// PreToolUse records the paths a turn touches; Stop reads them back to decide
// whether an architectural decision went unrecorded.

const STATE_DIR = join(tmpdir(), "claude-architect");
const DAY_MS = 24 * 60 * 60 * 1000;

function statePath(sessionId) {
  const safe = String(sessionId || "unknown").replace(/[^\w.-]/g, "_");
  return join(STATE_DIR, `${safe}.json`);
}

function prune() {
  try {
    const cutoff = Date.now() - DAY_MS;
    for (const name of readdirSync(STATE_DIR)) {
      const p = join(STATE_DIR, name);
      if (statSync(p).mtimeMs < cutoff) rmSync(p, { force: true });
    }
  } catch {
    /* pruning is best-effort */
  }
}

export function readState(sessionId) {
  try {
    const state = JSON.parse(readFileSync(statePath(sessionId), "utf8"));
    return {
      touched: Array.isArray(state.touched) ? state.touched : [],
      notified: Array.isArray(state.notified) ? state.notified : [],
      recorded: Boolean(state.recorded),
      gated: Boolean(state.gated),
      charterSent: Boolean(state.charterSent),
    };
  } catch {
    return {
      touched: [],
      notified: [],
      recorded: false,
      gated: false,
      charterSent: false,
    };
  }
}

export function writeState(sessionId, state) {
  try {
    mkdirSync(STATE_DIR, { recursive: true });
    prune();
    writeFileSync(statePath(sessionId), JSON.stringify(state), "utf8");
  } catch {
    /* state is an optimization, not a requirement */
  }
}

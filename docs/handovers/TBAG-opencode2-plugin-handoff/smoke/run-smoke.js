// Smoke test for tbag-ui/tui.tsx against mocked host modules.
// Proves: setup runs, slots render with null + full snapshots, the palette/
// slash command opens the panel, and keymap.layer is NEVER called during
// render (regression test for the "provider is missing" crash class).
const assert = require("node:assert/strict");
const Module = require("node:module");
const path = require("node:path");

const HERE = __dirname;
const redirect = {
  "solid-js": path.join(HERE, "mock-solid.js"),
  "@opencode/plugin/tui": path.join(HERE, "mock-plugin-tui.js"),
  "mock-jsx/jsx-runtime": path.join(HERE, "mock-jsx-runtime.js"),
};
const originalResolve = Module._resolveFilename;
Module._resolveFilename = function (request, ...rest) {
  if (redirect[request]) return redirect[request];
  return originalResolve.call(this, request, ...rest);
};

let phase = "setup";
const layerCalls = [];
const slotClaims = [];
let panelOpened = null;
globalThis.__recordLayer = (input) => layerCalls.push({ phase, layer: input() });

const SNAPSHOT = {
  format: "tbag-status-v1",
  run: { id: "R9", status: "active", parent_loop: "workers-running" },
  progress: { registered_percent: 42, registered_done: 5, registered_total: 12, phases_done: 0, phases_total: 1 },
  worker_budget: { live: 1, max: 4 },
  analysts_active: [{ task_id: "A1" }],
  grunts_active: [],
  current_phase: { phase_id: "repair", percent: 42, gate: { result: "pending" } },
  workers: [
    {
      tier: "analyst", authority: "Planner", role: "planner", elapsed_seconds: 61,
      task_id: "PLAN-1", objective: "plan things", model: "mock-model",
      session: { id: "ses_abcdef1234567890" },
      process: { worker: { alive: true, cpu_percent: 1.5, cpu_seconds: 4 } },
      observer: { healthy: true, known: true },
      log_age_seconds: 5, report_age_seconds: 6, deadline: { exceeded: false },
    },
    {
      tier: "grunt", role: "implementer", elapsed_seconds: 3600,
      task_id: "T01", model: "mock-model", session: {},
      process_alive: false, attention: "silent-long-running",
      log_age_seconds: 7, report_age_seconds: 8,
    },
  ],
  attention: [{ phase_id: "repair", task_id: "T01", status: "attention", objective: "fix me" }],
  phases: [{ phase_id: "repair", complete: false, percent: 42, gate: {} }],
};

global.Bun = {
  spawnSync() {
    return { exitCode: 0, stdout: Buffer.from(JSON.stringify(SNAPSHOT)) };
  },
};

let route = { type: "home" };
const ctx = {
  location: undefined,
  data: {
    listen() { return () => {}; },
    location: { default: () => ({ directory: "/proj" }) },
  },
  ui: {
    router: { current: () => route },
    slot(claim) { slotClaims.push(claim); return () => {}; },
    panel: {
      open: (name) => { panelOpened = name; return true; },
      close: () => {},
    },
  },
  keymap: {
    // Faithful host emulation (proven against beta-19289): layers are owned
    // by the calling component, so layering during setup() throws while
    // layering inside a rendered component works.
    layer(input) {
      if (phase === "setup") throw new Error("Keymap provider is missing");
      layerCalls.push({ phase, layer: input() });
    },
    dispatch() {},
    shortcuts: () => [],
    commands: () => [],
    pending: () => [],
    active: () => [],
    mode: { current: () => "base", push: () => () => {} },
  },
};

async function flush(times = 5) {
  for (let i = 0; i < times; i++) await new Promise((r) => setImmediate(r));
}

function textOf(node) {
  if (node === null || node === undefined) return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("|");
  if (typeof node === "object") {
    if (node.props && "children" in node.props) return textOf(node.props.children);
    return JSON.stringify(node).slice(0, 200);
  }
  return "";
}

(async () => {
  const compiled = process.env.SMOKE_COMPILED || "./compiled/tui-under-test.js";
  const plugin = require(compiled).default;
  assert.equal(plugin.id, "tbag.status.tui");
  assert.equal(typeof plugin.setup, "function");

  let cleanup;
  try {
    cleanup = plugin.setup(ctx);
  } catch (error) {
    console.error("TBAG_UI_SMOKE_FAIL setup threw:", error);
    process.exit(1);
  }
  assert.equal(typeof cleanup, "function");
  // The fixed file must not layer during setup (host throws there).
  assert.equal(layerCalls.filter((c) => c.phase === "setup").length, 0);

  const byAppend = Object.fromEntries(slotClaims.map((c) => [c.append, c]));
  assert.ok(byAppend["prompt.footer.status"]);
  assert.ok(byAppend["sidebar.content"]);
  assert.ok(byAppend["session.panel"]);

  phase = "render";
  // Footer with no session route renders nothing and never touches keymap.
  route = { type: "home" };
  assert.equal(byAppend["prompt.footer.status"].render(), null);

  // With a session route, footer renders after the snapshot microtask lands.
  route = { type: "session", sessionID: "ses-test" };
  let footer = byAppend["prompt.footer.status"].render();
  await flush();
  footer = byAppend["prompt.footer.status"].render();
  assert.match(textOf(footer), /T-BAG ACTIVE/);
  assert.match(textOf(footer), /█/);

  const sidebar = byAppend["sidebar.content"].render({ sessionID: "ses-test" });
  assert.match(textOf(sidebar), /PLAN-1/);
  assert.match(textOf(sidebar), /1 item.*attention|attention/);

  // Panel with a foreign name renders nothing; ours renders fallback, then data.
  const other = byAppend["session.panel"].render({ name: "other", sessionID: "ses-test" });
  assert.equal(textOf(other), "");
  const panel = byAppend["session.panel"].render({ name: "tbag.status", sessionID: "ses-test" });
  assert.match(textOf(panel), /T-BAG · R9 · /);
  assert.match(textOf(panel), /ACTIVE/);
  assert.match(textOf(panel), /PHASES/);
  assert.match(textOf(panel), /\[1\] /);
  assert.match(textOf(panel), /Planner/);
  assert.match(textOf(panel), /\[2\] /);
  assert.match(textOf(panel), /Worker/);
  assert.match(textOf(panel), /ATTENTION · 1/);

  // Palette/slash command opens the panel (layer registered during render).
  const renderLayers = layerCalls.filter((c) => c.phase === "render");
  assert.ok(renderLayers.length >= 1);
  assert.equal(renderLayers[0].layer.commands[0].id, "tbag.status");
  assert.equal(renderLayers[0].layer.commands[0].slash.name, "tbag");
  renderLayers[0].layer.commands[0].run();
  assert.equal(panelOpened, "tbag.status");

  cleanup();
  console.log("TBAG_UI_SMOKE_PASS");
  process.exit(0);
})().catch((error) => {
  console.error("TBAG_UI_SMOKE_FAIL", error);
  process.exit(1);
});

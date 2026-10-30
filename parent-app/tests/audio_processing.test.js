import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { DemoParentApiClient } from "./support/demo_api.js";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const deviceSource = readFileSync(join(root, "src", "views_device.js"), "utf8");
const stateSource = readFileSync(join(root, "src", "state.js"), "utf8");

test("device view exposes lightweight microphone cleanup and explicit enhanced opt-in", () => {
  assert.match(deviceSource, /tr\("device\.mic\.improve"\)/);
  assert.match(deviceSource, /tr\("device\.mic\.advanced"\)/);
  assert.match(deviceSource, /tr\("device\.mic\.advanced_help"\)/);
  assert.match(deviceSource, /available\.advanced/);
});

test("state fetches audio only through the advertised Parent capability", () => {
  assert.match(stateSource, /settings\.audio/);
  assert.match(stateSource, /this\.api\.audio\(\)/);
  assert.match(stateSource, /refreshAudio/);
});

test("test fixture defaults to lightweight cleanup even when enhanced processing exists", async () => {
  const api = new DemoParentApiClient();
  const index = await api.index();
  assert.equal(index.capabilities["settings.audio"], true);
  const initial = await api.audio();
  assert.equal(initial.desired.microphone_processing_enabled, true);
  assert.equal(initial.desired.advanced_noise_reduction, false);
  assert.equal(initial.effective.microphone_processing_mode, "lightweight");
  assert.equal(initial.available.advanced, true);
});

test("test fixture changes enhanced mode only after an explicit Parent update", async () => {
  const api = new DemoParentApiClient();
  const advanced = await api.updateAudio({ advanced_noise_reduction: true });
  assert.equal(advanced.effective.microphone_processing_mode, "advanced");
  const disabled = await api.updateAudio({ microphone_processing_enabled: false });
  assert.equal(disabled.effective.microphone_processing_mode, "off");
  const reset = await api.resetAudio();
  assert.equal(reset.effective.microphone_processing_mode, "lightweight");
  assert.equal(reset.desired.advanced_noise_reduction, false);
});

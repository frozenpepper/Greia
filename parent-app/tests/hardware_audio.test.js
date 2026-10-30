import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { DemoParentApiClient } from "./support/demo_api.js";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const deviceSource = readFileSync(join(root, "src", "views_device.js"), "utf8");

test("device view exposes Greia microphone gain when hardware reports it", () => {
  assert.match(deviceSource, /mic_gain/);
  assert.match(deviceSource, /tr\("device\.hardware\.microphone"\)/);
  assert.match(deviceSource, /min:\s*0\.5/);
  assert.match(deviceSource, /max:\s*4/);
});

test("test fixture hardware mirrors Greia microphone gain defaults and updates", async () => {
  const api = new DemoParentApiClient();
  const initial = await api.hardware();
  assert.equal(initial.desired.mic_gain, 2.0);

  const updated = await api.updateHardware({ mic_gain: 3.25 });
  assert.equal(updated.desired.mic_gain, 3.25);

  const reset = await api.resetHardware();
  assert.equal(reset.desired.mic_gain, 2.0);
});

test("test fixture rejects microphone gain outside Greia platform bounds", async () => {
  const api = new DemoParentApiClient();
  await assert.rejects(api.updateHardware({ mic_gain: 0.25 }), /between 50% and 400%/);
  await assert.rejects(api.updateHardware({ mic_gain: 4.25 }), /between 50% and 400%/);
});

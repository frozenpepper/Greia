import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { ParentApiClient } from "../src/api.js";
import { DemoManagementApiClient } from "./support/demo_management_api.js";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const viewSource = readFileSync(join(root, "src", "views_system_controls.js"), "utf8");
const stateSource = readFileSync(join(root, "src", "state.js"), "utf8");
const layoutSource = readFileSync(join(root, "src", "views_device_layout.js"), "utf8");

const jsonResponse = (status, body) => ({
  ok: status >= 200 && status < 300,
  status,
  headers: { get: () => "application/json" },
  json: async () => body,
  text: async () => JSON.stringify(body),
});

test("system controls client uses the versioned Greia API and supports partial typed updates", async () => {
  const seen = [];
  const api = new ParentApiClient({
    origin: "http://greia.local:8766",
    fetchImpl: async (url, options) => {
      seen.push({ url, options });
      return jsonResponse(200, {
        schema_version: 1,
        volume_percent: 35,
        muted: true,
        brightness_percent: 100,
      });
    },
  });

  await api.systemControls();
  await api.updateSystemControls({ volumePercent: 35, muted: true });
  await api.updateSystemControls({ muted: false });

  assert.equal(seen[0].url, "http://greia.local:8766/api/v1/settings/system-controls");
  assert.equal(seen[0].options.method, "GET");
  assert.equal(seen[1].url, "http://greia.local:8766/api/v1/settings/system-controls");
  assert.equal(seen[1].options.method, "PUT");
  assert.deepEqual(JSON.parse(seen[1].options.body), {
    volume_percent: 35,
    muted: true,
  });
  assert.deepEqual(JSON.parse(seen[2].options.body), { muted: false });
});

test("system controls client rejects invalid and browser-unsupported fields before network", () => {
  const api = new ParentApiClient({ fetchImpl: async () => { throw new Error("network must not run"); } });
  assert.throws(() => api.updateSystemControls({ volumePercent: -1 }), /0 through 100/);
  assert.throws(() => api.updateSystemControls({ volumePercent: 101 }), /0 through 100/);
  assert.throws(() => api.updateSystemControls({ volumePercent: 25.5 }), /0 through 100/);
  assert.throws(() => api.updateSystemControls({ muted: "yes" }), /boolean/);
  assert.throws(() => api.updateSystemControls({ brightnessPercent: 40 }), /Unsupported system control field/);
  assert.throws(() => api.updateSystemControls({ volumePercent: 40, brightnessPercent: 40 }), /Unsupported system control field/);
});

test("test fixture advertises and strictly round-trips speaker volume and mute", async () => {
  const api = new DemoManagementApiClient();
  const index = await api.index();
  assert.equal(index.capabilities["settings.system_controls"], true);

  const initial = await api.systemControls();
  assert.equal(initial.volume_percent, 70);
  assert.equal(initial.muted, false);
  assert.equal(initial.brightness_percent, 100);

  const updated = await api.updateSystemControls({ volumePercent: 25, muted: true });
  assert.equal(updated.volume_percent, 25);
  assert.equal(updated.muted, true);
  assert.equal(updated.brightness_percent, 100);

  await assert.rejects(api.updateSystemControls({ brightnessPercent: 40 }), /Unsupported system control field/);
  await assert.rejects(
    api.updateSystemControls({ volumePercent: 40, brightnessPercent: 40 }),
    /Unsupported system control field/,
  );
  assert.equal((await api.systemControls()).brightness_percent, 100);
  assert.equal((await api.systemControls()).volume_percent, 25);
});

test("device UI is capability-gated, race-aware, and separate from microphone cleanup", () => {
  assert.match(stateSource, /settings\.system_controls/);
  assert.match(stateSource, /systemControls/);
  assert.match(layoutSource, /_systemControlsCard/);
  assert.match(viewSource, /tr\("device\.sound\.title"\)/);
  assert.match(viewSource, /tr\("device\.sound\.volume_label"\)/);
  assert.match(viewSource, /tr\("device\.sound\.mute"\)/);
  assert.match(viewSource, /nextVolume !== volume/);
  assert.match(viewSource, /nextMuted !== muted/);
  assert.match(
    viewSource,
    /save\.disabled = true;\s*try \{\s*if \(!Object\.keys\(patch\)\.length\) \{\s*await this\.state\.refreshSystemControls\(\)/s,
  );
  assert.match(viewSource, /catch \(error\) \{\s*this\.showFlash/s);
  assert.doesNotMatch(viewSource, /brightness_percent/);
  assert.doesNotMatch(viewSource, /microphone_processing/);
  assert.doesNotMatch(viewSource, /amixer|xrandr|\/sys\/class\/backlight/);
});

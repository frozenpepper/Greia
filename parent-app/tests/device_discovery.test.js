import test from "node:test";
import assert from "node:assert/strict";
import { DeviceScopedCredentialStore, GreiaDeviceDiscoveryClient, validDevice } from "../src/device_discovery.js";

const response = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body });

test("direct Greia hosting is detected when discovery bridge is absent", async () => {
  const discovery = new GreiaDeviceDiscoveryClient({ fetchImpl: async () => response(404, {}), storage: null });
  assert.equal(await discovery.discover(), null);
});

test("discovery exposes only validated Greia device records", async () => {
  const discovery = new GreiaDeviceDiscoveryClient({
    storage: null,
    fetchImpl: async () => response(200, { devices: [
      { origin: "https://192.168.1.20:8766", device_name: "Kids room", api_version: "v1", host: "192.168.1.20" },
      { origin: "http://evil.local:9999", device_name: "Not Greia", api_version: "v1" },
      { origin: "https://192.168.1.21:8766", device_name: "Wrong API", api_version: "v0" },
    ] }),
  });
  const result = await discovery.discover();
  assert.deepEqual(result.devices.map((device) => device.device_name), ["Kids room"]);
});

test("device selection remembers the exact validated Greia origin", async () => {
  const values = new Map();
  const storage = { getItem: (key) => values.get(key) || null, setItem: (key, value) => values.set(key, value), removeItem: (key) => values.delete(key) };
  const discovery = new GreiaDeviceDiscoveryClient({
    storage,
    fetchImpl: async (_url, options) => response(200, { device: { origin: JSON.parse(options.body).origin, device_name: "Living room", api_version: "v1" } }),
  });
  const selected = await discovery.select("https://192.168.1.42:8766");
  assert.equal(selected.origin, "https://192.168.1.42:8766");
  assert.equal(discovery.preferredOrigin(), selected.origin);
});

test("pairing credentials are scoped to the selected Greia, not the local proxy origin", () => {
  const credentials = new Map();
  const base = { get: (key) => credentials.get(key) || "", set: (key, value) => credentials.set(key, value), remove: (key) => credentials.delete(key) };
  const first = new DeviceScopedCredentialStore(base, "https://192.168.1.10:8766");
  const second = new DeviceScopedCredentialStore(base, "https://192.168.1.11:8766");
  first.set("http://127.0.0.1:8080", "first-token");
  second.set("http://127.0.0.1:8080", "second-token");
  assert.equal(first.get(), "first-token");
  assert.equal(second.get(), "second-token");
  assert.equal(credentials.size, 2);
});

test("device validation accepts only HTTPS Parent API v1 on port 8766", () => {
  assert.equal(validDevice({ origin: "https://10.0.0.2:8766", device_name: "Greia", api_version: "v1" }), true);
  assert.equal(validDevice({ origin: "https://10.0.0.2:8766", device_name: "Greia", api_version: 1 }), true);
  assert.equal(validDevice({ origin: "http://10.0.0.2:8766", device_name: "Greia", api_version: "v1" }), false);
  assert.equal(validDevice({ origin: "https://10.0.0.2:8080", device_name: "Greia", api_version: "v1" }), false);
});

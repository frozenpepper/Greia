import test from "node:test";
import assert from "node:assert/strict";
import { discoveryCandidates, discoverGreiaDevices, isLocalIpv4, validGreiaMeta } from "../tools/greia_discovery.mjs";

const interfaces = { wifi: [{ family: "IPv4", internal: false, address: "192.168.50.40", netmask: "255.255.255.0" }] };

test("LAN discovery scans the local bounded subnet and localhost", () => {
  const candidates = discoveryCandidates(interfaces);
  assert.ok(candidates.includes("127.0.0.1"));
  assert.ok(candidates.includes("192.168.50.1"));
  assert.ok(candidates.includes("192.168.50.254"));
  assert.ok(candidates.length <= 512);
});

test("large local networks are bounded instead of sweeping the whole subnet", () => {
  const candidates = discoveryCandidates({ wifi: [{ family: "IPv4", internal: false, address: "10.23.44.9", netmask: "255.255.0.0" }] });
  assert.ok(candidates.includes("10.23.44.1"));
  assert.ok(candidates.includes("10.23.44.254"));
  assert.equal(candidates.includes("10.23.45.1"), false);
  assert.ok(candidates.length <= 512);
});

test("only local IPv4 ranges are eligible for discovery", () => {
  assert.equal(isLocalIpv4("192.168.1.2"), true);
  assert.equal(isLocalIpv4("10.1.2.3"), true);
  assert.equal(isLocalIpv4("172.20.1.3"), true);
  assert.equal(isLocalIpv4("8.8.8.8"), false);
});

test("Greia meta validation is exact enough to reject unrelated web servers", () => {
  assert.equal(validGreiaMeta({ product: "Greia", service: "Greia Parents", api_version: "v1", device_name: "Bedroom" }), true);
  assert.equal(validGreiaMeta({ product: "Greia", service: "Greia Parents", api_version: 1, device_name: "Bedroom" }), true);
  assert.equal(validGreiaMeta({ product: "Greia", service: "Other", api_version: "v1", device_name: "Bedroom" }), false);
  assert.equal(validGreiaMeta({ product: "Greia", service: "Greia Parents", api_version: "v0", device_name: "Bedroom" }), false);
});

test("discovery returns only successful validated probes and deduplicates them", async () => {
  const found = await discoverGreiaDevices({
    interfaces,
    concurrency: 16,
    probe: async (origin) => origin.endsWith("192.168.50.23:8766") ? {
      origin,
      host: "192.168.50.23",
      port: 8766,
      device_name: "Bedroom",
      api_version: "v1",
      transport_security: "provisional-http",
    } : null,
  });
  assert.deepEqual(found.map((device) => device.device_name), ["Bedroom"]);
});

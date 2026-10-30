import test from "node:test";
import assert from "node:assert/strict";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { buildRuntimeManifest, discoverRuntimeFiles } from "../tools/runtime_manifest.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

test("runtime manifest follows the actual browser dependency closure", () => {
  const files = discoverRuntimeFiles(root);
  for (const required of [
    "index.html",
    "assets/greia-mark-light.svg",
    "src/app.js",
    "src/api.js",
    "src/device_discovery.js",
    "styles/app.css",
    "styles/management.css",
  ]) assert.ok(files.includes(required), `missing runtime dependency ${required}`);
  assert.equal(files.some((name) => name.startsWith("tests/")), false);
  assert.equal(files.some((name) => name.startsWith("tools/")), false);
  assert.equal(files.includes("assets/greia-constellation.png"), false);
});

test("runtime manifest hashes every discovered file exactly once", () => {
  const revision = "a".repeat(40);
  const files = discoverRuntimeFiles(root);
  const manifest = buildRuntimeManifest(root, revision);
  assert.equal(manifest.schema_version, 1);
  assert.equal(manifest.revision, revision);
  assert.deepEqual(Object.keys(manifest.files), files);
  for (const entry of Object.values(manifest.files)) {
    assert.equal(Number.isInteger(entry.bytes) && entry.bytes > 0, true);
    assert.match(entry.sha256, /^[0-9a-f]{64}$/);
  }
});

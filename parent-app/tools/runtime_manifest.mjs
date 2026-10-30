import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { extname, posix, resolve } from "node:path";

const REMOTE_SCHEME = /^[a-z][a-z0-9+.-]*:/i;
const JS_IMPORT = /(?:^|\n)\s*(?:import|export)\s+(?:[^;\n]*?\s+from\s+)?["']([^"']+)["']/g;
const CSS_IMPORT = /@import\s+(?:url\()?\s*["']([^"']+)["']\s*\)?/gi;
const CSS_URL = /url\(\s*["']?([^"')]+)["']?\s*\)/gi;
const HTML_REFERENCE = /<(?:script\b[^>]*\bsrc|link\b[^>]*\bhref|img\b[^>]*\bsrc|source\b[^>]*\bsrc)\s*=\s*["']([^"']+)["'][^>]*>/gi;

// Diagnostic mirror of tools/update_parent_client_pin.py (the repository-root
// tool owns the authoritative pin, manifest and image overlay).
export class RuntimeManifestError extends Error {}

function localReference(base, reference) {
  const raw = String(reference).trim();
  if (!raw || raw.startsWith("#") || raw.startsWith("data:")) return null;
  if (REMOTE_SCHEME.test(raw) || raw.startsWith("//")) throw new RuntimeManifestError(`remote runtime dependency is forbidden: ${raw}`);
  const clean = raw.split(/[?#]/, 1)[0];
  if (!clean) return null;
  if (clean.startsWith("/")) throw new RuntimeManifestError(`runtime dependency must be package-relative: ${raw}`);
  const normalized = posix.normalize(posix.join(posix.dirname(base), clean));
  if (normalized === ".." || normalized.startsWith("../")) throw new RuntimeManifestError(`runtime dependency escapes checkout: ${raw}`);
  if (normalized.split("/").some((part) => part.startsWith("."))) throw new RuntimeManifestError(`hidden runtime path is not supported: ${normalized}`);
  return normalized;
}

function referencesFor(relative, bytes) {
  const suffix = extname(relative).toLowerCase();
  if (![".html", ".js", ".css"].includes(suffix)) return [];
  const text = bytes.toString("utf8");
  const raw = [];
  if (suffix === ".html") {
    for (const match of text.matchAll(HTML_REFERENCE)) {
      const tag = match[0].toLowerCase();
      if (tag.startsWith("<link") && !/\brel\s*=\s*["'][^"']*stylesheet/i.test(match[0])) continue;
      raw.push(match[1]);
    }
  } else if (suffix === ".js") {
    for (const match of text.matchAll(JS_IMPORT)) raw.push(match[1]);
  } else {
    for (const match of text.matchAll(CSS_IMPORT)) raw.push(match[1]);
    for (const match of text.matchAll(CSS_URL)) raw.push(match[1]);
  }
  return raw.map((reference) => localReference(relative, reference)).filter(Boolean);
}

export function discoverRuntimeFiles(root) {
  const checkout = resolve(root);
  const pending = ["index.html"];
  const visited = new Set();
  while (pending.length) {
    const relative = pending.pop();
    if (visited.has(relative)) continue;
    const absolute = resolve(checkout, relative);
    if (absolute !== checkout && !absolute.startsWith(`${checkout}/`)) throw new RuntimeManifestError(`runtime file escapes checkout: ${relative}`);
    let bytes;
    try { bytes = readFileSync(absolute); }
    catch (error) { throw new RuntimeManifestError(`referenced runtime file is missing: ${relative}`, { cause: error }); }
    visited.add(relative);
    for (const dependency of referencesFor(relative, bytes)) if (!visited.has(dependency)) pending.push(dependency);
  }
  return [...visited].sort();
}

export function buildRuntimeManifest(root, revision) {
  if (!/^[0-9a-f]{40}$/.test(revision)) throw new RuntimeManifestError("revision must be an exact lowercase 40-character Git SHA");
  const checkout = resolve(root);
  const files = {};
  for (const relative of discoverRuntimeFiles(checkout)) {
    const bytes = readFileSync(resolve(checkout, relative));
    files[relative] = {
      bytes: bytes.length,
      sha256: createHash("sha256").update(bytes).digest("hex"),
    };
  }
  return {
    schema_version: 1,
    repository: "frozenpepper/Greia:parent-app",
    revision,
    files,
  };
}

export function writeRuntimeManifest(root, revision, output) {
  const manifest = buildRuntimeManifest(root, revision);
  writeFileSync(output, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  return manifest;
}

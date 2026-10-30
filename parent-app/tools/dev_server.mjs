import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { request as httpsRequest } from "node:https";
import { dirname, extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { discoverGreiaDevices, probeGreia } from "./greia_discovery.mjs";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const host = process.env.GREIA_PARENT_HOST || "127.0.0.1";
const port = Number(process.env.GREIA_PARENT_PORT || 8080);
const discoveryTtlMs = 5000;
const extraCandidate = process.argv[2] || process.env.GREIA_PARENT_TARGET || "";

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error("GREIA_PARENT_PORT must be a valid TCP port");
}

const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".webp", "image/webp"],
  [".ico", "image/x-icon"],
]);
const allowedStaticRoots = new Set(["src", "styles", "assets"]);
let discoveryCache = { at: 0, devices: [] };
let selectedDevice = null;

function writeJson(res, status, payload) {
  const body = Buffer.from(JSON.stringify(payload));
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "content-length": body.length,
    "cache-control": "no-store",
  });
  res.end(body);
}

async function readJsonBody(req, limit = 4096) {
  const chunks = [];
  let bytes = 0;
  for await (const chunk of req) {
    bytes += chunk.length;
    if (bytes > limit) throw new Error("request body is too large");
    chunks.push(chunk);
  }
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function staticPath(pathname) {
  if (pathname === "/") return join(root, "index.html");
  let decoded;
  try { decoded = decodeURIComponent(pathname); }
  catch { return null; }
  if (!decoded.startsWith("/") || decoded.includes("\\") || decoded.includes("\0")) return null;
  const relative = normalize(decoded.slice(1));
  if (!relative || relative === "." || relative.startsWith("..")) return null;
  const first = relative.split(/[\\/]/, 1)[0];
  if (!allowedStaticRoots.has(first)) return null;
  const candidate = join(root, relative);
  if (!candidate.startsWith(`${root}/`) && !candidate.startsWith(`${root}\\`)) return null;
  return candidate;
}

async function discover({ force = false } = {}) {
  const now = Date.now();
  if (!force && now - discoveryCache.at < discoveryTtlMs) return discoveryCache.devices;
  const devices = await discoverGreiaDevices();
  if (extraCandidate) {
    const candidate = await probeGreia(extraCandidate);
    if (candidate && !devices.some((device) => device.origin === candidate.origin)) devices.push(candidate);
  }
  devices.sort((a, b) => a.device_name.localeCompare(b.device_name) || a.origin.localeCompare(b.origin));
  discoveryCache = { at: now, devices };
  if (selectedDevice && !devices.some((device) => device.origin === selectedDevice.origin)) selectedDevice = null;
  return devices;
}

function proxyHeaders(req, target) {
  const headers = { ...req.headers, host: target.host };
  delete headers.connection;
  if (headers.origin) headers.origin = target.origin;
  if (headers.referer) {
    try {
      const source = new URL(headers.referer);
      headers.referer = new URL(`${source.pathname}${source.search}`, `${target.origin}/`).href;
    } catch {
      delete headers.referer;
    }
  }
  return headers;
}

function proxyApi(req, res) {
  if (!selectedDevice) {
    writeJson(res, 409, { error: { code: "greia_device_not_selected", message: "Choose a Greia first." } });
    return;
  }
  const target = new URL(selectedDevice.origin);
  const upstreamUrl = new URL(req.url, target);
  const upstream = httpsRequest({
    // Local Greia uses a self-signed HTTPS certificate.
    rejectUnauthorized: false,
    protocol: upstreamUrl.protocol,
    hostname: upstreamUrl.hostname,
    port: upstreamUrl.port,
    method: req.method,
    path: `${upstreamUrl.pathname}${upstreamUrl.search}`,
    headers: proxyHeaders(req, target),
  }, (upstreamResponse) => {
    const responseHeaders = { ...upstreamResponse.headers };
    delete responseHeaders.connection;
    res.writeHead(upstreamResponse.statusCode || 502, responseHeaders);
    upstreamResponse.pipe(res);
  });
  upstream.setTimeout(5000, () => upstream.destroy());
  upstream.on("error", () => {
    if (res.headersSent) { res.destroy(); return; }
    writeJson(res, 502, {
      error: {
        code: "selected_greia_unreachable",
        message: "The selected Greia is no longer reachable.",
      },
    });
  });
  req.pipe(upstream);
}

async function handleDiscovery(req, res, url) {
  if (url.pathname === "/__greia/devices" && req.method === "GET") {
    try {
      const devices = await discover({ force: url.searchParams.get("refresh") === "1" });
      writeJson(res, 200, { devices, selected_origin: selectedDevice?.origin || null });
    } catch {
      writeJson(res, 500, { error: { code: "device_discovery_failed", message: "Greia device discovery failed." } });
    }
    return true;
  }
  if (url.pathname === "/__greia/selected" && req.method === "GET") {
    writeJson(res, 200, { device: selectedDevice });
    return true;
  }
  if (url.pathname === "/__greia/select" && req.method === "POST") {
    try {
      const body = await readJsonBody(req);
      const origin = typeof body.origin === "string" ? body.origin : "";
      const devices = await discover();
      const device = devices.find((item) => item.origin === origin);
      if (!device) {
        writeJson(res, 400, { error: { code: "device_not_discovered", message: "That Greia was not found on this network." } });
        return true;
      }
      selectedDevice = device;
      writeJson(res, 200, { device });
    } catch {
      writeJson(res, 400, { error: { code: "invalid_device_selection", message: "Could not select that Greia." } });
    }
    return true;
  }
  return false;
}

async function serveStatic(req, res, pathname) {
  const candidate = staticPath(pathname);
  if (!candidate) {
    res.writeHead(404, { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" });
    res.end("Not found\n");
    return;
  }
  try {
    const info = await stat(candidate);
    const contentType = contentTypes.get(extname(candidate).toLowerCase());
    if (!info.isFile() || !contentType) throw new Error("not a supported file");
    res.writeHead(200, {
      "content-type": contentType,
      "content-length": info.size,
      "cache-control": "no-store",
    });
    if (req.method === "HEAD") { res.end(); return; }
    createReadStream(candidate).pipe(res);
  } catch {
    res.writeHead(404, { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" });
    res.end("Not found\n");
  }
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${host}:${port}`);
  if (await handleDiscovery(req, res, url)) return;
  if (url.pathname === "/api/v1" || url.pathname.startsWith("/api/v1/")) {
    proxyApi(req, res);
    return;
  }
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { "content-type": "text/plain; charset=utf-8", "allow": "GET, HEAD" });
    res.end("Method not allowed\n");
    return;
  }
  await serveStatic(req, res, url.pathname);
});

server.listen(port, host, () => {
  console.log(`Greia Parent app: http://${host}:${port}`);
  console.log("Searching the local network for Greia devices on Parent API port 8766.");
  console.log("Open the Parent app and choose a discovered Greia. There is no demo mode.");
});

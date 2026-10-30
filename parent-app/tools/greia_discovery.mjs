import { request as httpsRequest } from "node:https";
import { networkInterfaces } from "node:os";

export const GREIA_PARENT_PORT = 8766;
export const GREIA_API_VERSION = "v1";
export const MAX_DISCOVERY_HOSTS = 512;
export const PROBE_TIMEOUT_MS = 750;
export const PROBE_BODY_LIMIT = 16 * 1024;

const ipv4ToInt = (address) => {
  const parts = String(address).split(".").map(Number);
  if (parts.length !== 4 || parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) return null;
  return (((parts[0] << 24) >>> 0) | (parts[1] << 16) | (parts[2] << 8) | parts[3]) >>> 0;
};

const intToIpv4 = (value) => [24, 16, 8, 0].map((shift) => (value >>> shift) & 255).join(".");

export function isLocalIpv4(address) {
  const value = ipv4ToInt(address);
  if (value === null) return false;
  const a = value >>> 24;
  const b = (value >>> 16) & 255;
  return a === 10
    || (a === 172 && b >= 16 && b <= 31)
    || (a === 192 && b === 168)
    || (a === 169 && b === 254)
    || a === 127;
}

function interfaceCandidates(address, netmask, maxHosts) {
  const ip = ipv4ToInt(address);
  const mask = ipv4ToInt(netmask);
  if (ip === null || mask === null || !isLocalIpv4(address)) return [];
  const network = (ip & mask) >>> 0;
  const broadcast = (network | (~mask >>> 0)) >>> 0;
  const hostCount = Math.max(0, broadcast - network - 1);
  let start = network + 1;
  let end = broadcast - 1;
  if (hostCount > maxHosts) {
    const local24 = ip & 0xffffff00;
    start = local24 + 1;
    end = local24 + 254;
  }
  const result = [];
  for (let value = start; value <= end && result.length < maxHosts; value += 1) {
    result.push(intToIpv4(value >>> 0));
  }
  return result;
}

export function discoveryCandidates(interfaces = networkInterfaces(), { maxHosts = MAX_DISCOVERY_HOSTS } = {}) {
  const candidates = new Set(["127.0.0.1"]);
  for (const records of Object.values(interfaces || {})) {
    for (const record of records || []) {
      const family = typeof record.family === "string" ? record.family : record.family === 4 ? "IPv4" : "";
      if (family !== "IPv4" || record.internal || !isLocalIpv4(record.address)) continue;
      for (const address of interfaceCandidates(record.address, record.netmask || "255.255.255.0", maxHosts)) {
        candidates.add(address);
        if (candidates.size >= maxHosts) break;
      }
      if (candidates.size >= maxHosts) break;
    }
    if (candidates.size >= maxHosts) break;
  }
  return [...candidates].slice(0, maxHosts);
}

export function validGreiaMeta(payload) {
  const version = payload?.api_version;
  const versionMatches = version === GREIA_API_VERSION || version === 1 || version === "1";
  return Boolean(
    payload
    && typeof payload === "object"
    && payload.product === "Greia"
    && payload.service === "Greia Parents"
    && versionMatches
    && typeof payload.device_name === "string"
    && payload.device_name.trim(),
  );
}

export function probeGreia(origin, {
  timeoutMs = PROBE_TIMEOUT_MS,
  requestImpl = httpsRequest,
} = {}) {
  return new Promise((resolve) => {
    let url;
    try { url = new URL("/api/v1/meta", origin); }
    catch { resolve(null); return; }
    if (url.protocol !== "https:" || Number(url.port || 443) !== GREIA_PARENT_PORT) {
      resolve(null);
      return;
    }
    let settled = false;
    let timer = null;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      resolve(value);
    };
    timer = setTimeout(() => {
      req.destroy();
      finish(null);
    }, timeoutMs);
    const req = requestImpl({
      protocol: url.protocol,
      // Installed Greia uses a self-signed certificate for its home LAN.
      rejectUnauthorized: false,
      hostname: url.hostname,
      port: url.port,
      method: "GET",
      path: url.pathname,
      headers: { Accept: "application/json", Connection: "close" },
    }, (res) => {
      if (res.statusCode !== 200) {
        res.resume?.();
        finish(null);
        return;
      }
      let bytes = 0;
      const chunks = [];
      res.on("data", (chunk) => {
        bytes += chunk.length;
        if (bytes > PROBE_BODY_LIMIT) {
          req.destroy();
          finish(null);
          return;
        }
        chunks.push(chunk);
      });
      res.on("end", () => {
        if (settled) return;
        try {
          const payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
          if (!validGreiaMeta(payload)) { finish(null); return; }
          finish({
            origin: `${url.protocol}//${url.hostname}:${url.port}`,
            host: url.hostname,
            port: Number(url.port),
            device_name: payload.device_name.trim(),
            api_version: typeof payload.api_version === "number" ? `v${payload.api_version}` : String(payload.api_version),
            transport_security: payload.transport_security || null,
          });
        } catch {
          finish(null);
        }
      });
      res.on("error", () => finish(null));
    });
    req.setTimeout?.(timeoutMs, () => req.destroy());
    req.on("error", () => finish(null));
    req.end();
  });
}

export async function discoverGreiaDevices({
  interfaces = networkInterfaces(),
  maxHosts = MAX_DISCOVERY_HOSTS,
  concurrency = 48,
  timeoutMs = PROBE_TIMEOUT_MS,
  probe = probeGreia,
} = {}) {
  const addresses = discoveryCandidates(interfaces, { maxHosts });
  const results = [];
  let cursor = 0;
  const worker = async () => {
    while (cursor < addresses.length) {
      const index = cursor;
      cursor += 1;
      const address = addresses[index];
      const result = await probe(`https://${address}:${GREIA_PARENT_PORT}`, { timeoutMs });
      if (result) results.push(result);
    }
  };
  const workerCount = Math.max(1, Math.min(Number(concurrency) || 1, addresses.length || 1, 64));
  await Promise.all(Array.from({ length: workerCount }, () => worker()));
  const unique = new Map(results.map((device) => [device.origin, device]));
  return [...unique.values()].sort((a, b) => a.device_name.localeCompare(b.device_name) || a.origin.localeCompare(b.origin));
}

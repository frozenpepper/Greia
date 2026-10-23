const PREFERRED_DEVICE_KEY = "greia-parent-preferred-origin";

export class GreiaDeviceDiscoveryClient {
  constructor({
    fetchImpl = globalThis.fetch?.bind(globalThis),
    storage = globalThis.localStorage ?? null,
  } = {}) {
    if (!fetchImpl) throw new TypeError("fetch implementation is required");
    this.fetchImpl = fetchImpl;
    this.storage = storage;
  }

  preferredOrigin() {
    try { return this.storage?.getItem(PREFERRED_DEVICE_KEY) || ""; }
    catch { return ""; }
  }

  remember(origin) {
    try {
      if (origin) this.storage?.setItem(PREFERRED_DEVICE_KEY, origin);
      else this.storage?.removeItem(PREFERRED_DEVICE_KEY);
    } catch {}
  }

  async discover({ refresh = false } = {}) {
    let response;
    try {
      response = await this.fetchImpl(`/__greia/devices${refresh ? "?refresh=1" : ""}`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
    } catch {
      return null;
    }
    if (response.status === 404) return null;
    const payload = await this.#json(response);
    if (!response.ok) throw new Error(payload?.error?.message || "Could not search for Greia devices.");
    const devices = Array.isArray(payload?.devices) ? payload.devices.filter(validDevice) : [];
    return { devices, selectedOrigin: typeof payload?.selected_origin === "string" ? payload.selected_origin : "" };
  }

  async select(origin) {
    const response = await this.fetchImpl("/__greia/select", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ origin }),
    });
    const payload = await this.#json(response);
    if (!response.ok || !validDevice(payload?.device)) {
      throw new Error(payload?.error?.message || "Could not connect to that Greia.");
    }
    this.remember(payload.device.origin);
    return payload.device;
  }

  async #json(response) {
    try { return await response.json(); }
    catch { return null; }
  }
}

export function validDevice(device) {
  if (!device || typeof device !== "object") return false;
  if (typeof device.origin !== "string" || !/^https:\/\/[^/]+:8766$/.test(device.origin)) return false;
  if (typeof device.device_name !== "string" || !device.device_name.trim()) return false;
  return device.api_version === "v1" || device.api_version === 1 || device.api_version === "1";
}

export class DeviceScopedCredentialStore {
  constructor(store, scopeOrigin) {
    if (!store) throw new TypeError("credential store is required");
    if (typeof scopeOrigin !== "string" || !scopeOrigin) throw new TypeError("credential scope origin is required");
    this.store = store;
    this.scopeOrigin = scopeOrigin;
  }
  get() { return this.store.get(this.scopeOrigin); }
  set(_origin, value) { this.store.set(this.scopeOrigin, value); }
  remove() { this.store.remove(this.scopeOrigin); }
}

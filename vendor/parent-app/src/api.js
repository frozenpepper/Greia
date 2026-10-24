export class ParentApiError extends Error {
  constructor(message, { status = 0, code = "request_failed", details = null } = {}) {
    super(message); this.name = "ParentApiError"; this.status = status; this.code = code; this.details = details;
  }
  get authenticationRequired() { return this.status === 401 || this.code === "pairing_required"; }
}
export const MAX_SOFTWARE_UPDATE_BYTES = 2 * 1024 * 1024 * 1024 + 1024 * 1024;
export const SOFTWARE_UPDATE_MEDIA_TYPE = "application/vnd.greia.software-update+zip";
export class ParentApiClient {
  constructor({ origin = globalThis.location?.origin ?? "https://127.0.0.1:8766", apiBase = "/api/v1", credentialStore = null, fetchImpl = globalThis.fetch?.bind(globalThis) } = {}) {
    if (!fetchImpl) throw new TypeError("fetch implementation is required");
    this.origin = String(origin).replace(/\/$/, ""); this.apiBase = apiBase.startsWith("/") ? apiBase : `/${apiBase}`; this.credentialStore = credentialStore; this.fetchImpl = fetchImpl;
  }
  async meta() { return this.#request("/meta", { authenticated: false }); }
  async index() { return this.#request(""); }
  async system() { return this.#request("/system"); }
  async systemUpdate() { return this.#request("/system/update"); }
  checkSystemUpdate() { return this.#request("/system/update/check", { method: "POST", body: {} }); }
  prepareSystemUpdate(releaseId) {
    if (typeof releaseId !== "string" || !releaseId.trim() || releaseId.length > 96) throw new TypeError("system update release id is required");
    return this.#request("/system/update/prepare", { method: "POST", body: { release_id: releaseId } });
  }
  restartSystemUpdate() { return this.#request("/system/update/restart", { method: "POST", body: {} }); }
  restartSoftwareUpdatePackage() { return this.#request("/system/update/package/restart", { method: "POST", body: {} }); }
  async profiles() { return this.#request("/profiles"); }
  async activities() { return this.#request("/activities"); }
  async hardware() { return this.#request("/settings/hardware"); }
  async systemControls() { return this.#request("/settings/system-controls"); }
  async audio() { return this.#request("/settings/audio"); }
  async language() { return this.#request("/settings/language"); }
  async devices() { return this.#request("/devices"); }
  async parentPassword() { return this.#request("/parent-password"); }
  async wifi() { return this.#request("/network/wifi"); }
  async ssh() { return this.#request("/maintenance/ssh"); }
  async usageLimits() { return this.#request("/usage-limits"); }
  updateUsageLimits(dailyMinutes) { if (dailyMinutes !== null && (!Number.isInteger(dailyMinutes) || dailyMinutes < 1 || dailyMinutes > 1440)) throw new TypeError("device daily minutes must be null or an integer from 1 through 1440"); return this.#request("/usage-limits", { method: "PUT", body: { daily_minutes: dailyMinutes } }); }
  profileUsageLimit(profileId) { if (typeof profileId !== "string" || !profileId) throw new TypeError("profile id is required"); return this.#request(`/profiles/${encodeURIComponent(profileId)}/usage-limit`); }
  updateProfileUsageLimit(profileId, dailyMinutes) { if (typeof profileId !== "string" || !profileId) throw new TypeError("profile id is required"); if (dailyMinutes !== null && (!Number.isInteger(dailyMinutes) || dailyMinutes < 1 || dailyMinutes > 1440)) throw new TypeError("profile daily minutes must be null or an integer from 1 through 1440"); return this.#request(`/profiles/${encodeURIComponent(profileId)}/usage-limit`, { method: "PUT", body: { daily_minutes: dailyMinutes } }); }
  async activityPolicy(profileId) { if (typeof profileId !== "string" || !profileId) throw new TypeError("profile id is required"); return this.#request(`/profiles/${encodeURIComponent(profileId)}/activity-policy`); }
  async updateActivityPolicy(profileId, policy) { if (typeof profileId !== "string" || !profileId) throw new TypeError("profile id is required"); if (!policy || typeof policy !== "object" || Array.isArray(policy)) throw new TypeError("Activity policy object is required"); return this.#request(`/profiles/${encodeURIComponent(profileId)}/activity-policy`, { method: "PUT", body: policy }); }
  async profilePresentation(profileId) { if (typeof profileId !== "string" || !profileId) throw new TypeError("profile id is required"); return this.#request(`/profiles/${encodeURIComponent(profileId)}/presentation`); }
  async updateProfilePresentation(profileId, { presentation, seedThemeIfUnset = false }) { if (typeof profileId !== "string" || !profileId) throw new TypeError("profile id is required"); if (!["neutral","boy","girl"].includes(presentation)) throw new TypeError("profile presentation must be neutral, boy, or girl"); return this.#request(`/profiles/${encodeURIComponent(profileId)}/presentation`, { method: "PUT", body: { presentation, seed_theme_if_unset: Boolean(seedThemeIfUnset) } }); }
  async changeParentPassword({ currentPassword, newPassword }) { return this.#request("/parent-password", { method: "PUT", body: { current_password: currentPassword, new_password: newPassword } }); }
  async updateLanguage(locale) { if (typeof locale !== "string" || !locale.trim()) throw new TypeError("Greia language locale is required"); return this.#request("/settings/language", { method: "PUT", body: { locale: locale.trim() } }); }
  updateSystemControls(settings) {
    if (!settings || typeof settings !== "object" || Array.isArray(settings)) throw new TypeError("System controls object is required");
    const allowed = new Set(["volumePercent", "muted"]);
    const unknown = Object.keys(settings).filter((key) => !allowed.has(key));
    if (unknown.length) throw new TypeError(`Unsupported system control field: ${unknown.sort().join(", ")}`);
    const body = {};
    if (Object.hasOwn(settings, "volumePercent")) {
      if (!Number.isInteger(settings.volumePercent) || settings.volumePercent < 0 || settings.volumePercent > 100) throw new TypeError("volume percent must be an integer from 0 through 100");
      body.volume_percent = settings.volumePercent;
    }
    if (Object.hasOwn(settings, "muted")) {
      if (typeof settings.muted !== "boolean") throw new TypeError("muted must be boolean");
      body.muted = settings.muted;
    }
    if (!Object.keys(body).length) throw new TypeError("At least one system control is required");
    return this.#request("/settings/system-controls", { method: "PUT", body });
  }
  async updateAudio(settings) { if (!settings || typeof settings !== "object" || Array.isArray(settings)) throw new TypeError("Audio settings object is required"); return this.#request("/settings/audio", { method: "PUT", body: settings }); }
  async resetAudio() { return this.#request("/settings/audio/reset", { method: "POST" }); }
  async connectWifi({ ssid, passphrase = "" }) { if (typeof ssid !== "string" || !ssid.trim()) throw new TypeError("Wi-Fi network name is required"); return this.#request("/network/wifi/connect", { method: "POST", body: { ssid: ssid.trim(), passphrase: String(passphrase || "") } }); }
  async updateSsh({ enabled, publicKey = null }) { return this.#request("/maintenance/ssh", { method: "PUT", body: { enabled: Boolean(enabled), public_key: typeof publicKey === "string" && publicKey.trim() ? publicKey.trim() : "" } }); }
  async progress(profileId = null) { const suffix = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : ""; return this.#request(`/progress${suffix}`); }
  async connectWithPassword({ password, deviceName }) { const result = await this.#request("/pairing/bootstrap", { method: "POST", authenticated: false, body: { password, device_name: deviceName } }); if (!result || typeof result.credential !== "string" || !result.credential) throw new ParentApiError("Greia did not return a device credential", { code: "invalid_authentication_response" }); this.credentialStore?.set(this.origin, result.credential); return result; }
  forgetCredential() { this.credentialStore?.remove(this.origin); }
  createProfile(profile) { return this.#request("/profiles", { method: "POST", body: profile }); }
  updateProfile(profileId, patch) { return this.#request(`/profiles/${encodeURIComponent(profileId)}`, { method: "PATCH", body: patch }); }
  deleteProfile(profileId) { return this.#request(`/profiles/${encodeURIComponent(profileId)}`, { method: "DELETE" }); }
  updateHardware(settings) { return this.#request("/settings/hardware", { method: "PUT", body: settings }); }
  resetHardware() { return this.#request("/settings/hardware/reset", { method: "POST" }); }
  revokeDevice(deviceId) { return this.#request(`/devices/${encodeURIComponent(deviceId)}`, { method: "DELETE" }); }
  installActivity(file) { if (!file || typeof file.arrayBuffer !== "function") throw new TypeError("Activity package file is required"); if (typeof file.name === "string" && !file.name.toLowerCase().endsWith(".greiaactivity")) throw new TypeError("Choose a .greiaactivity file"); return this.#request("/activities/install", { method: "POST", rawBody: file, contentType: "application/vnd.greia.activity+zip" }); }
  removeActivity(activityId) { if (typeof activityId !== "string" || !activityId.trim()) throw new TypeError("Activity id is required"); return this.#request(`/activities/${encodeURIComponent(activityId.trim())}`, { method: "DELETE" }); }
  uploadSystemUpdate(file) { if (!file || typeof file.arrayBuffer !== "function") throw new TypeError("System update file is required"); return this.#request("/system/update/bundle", { method: "POST", rawBody: file, contentType: "application/vnd.greia.system-update+zip" }); }
  uploadSoftwareUpdatePackage(file) {
    if (!file || typeof file.arrayBuffer !== "function") throw new TypeError("Software update package file is required");
    if (typeof file.name !== "string" || !file.name.toLowerCase().endsWith(".greia_update")) throw new TypeError("Choose a .greia_update package");
    if (!Number.isFinite(file.size) || file.size <= 0 || file.size > MAX_SOFTWARE_UPDATE_BYTES) throw new TypeError("Software update package size is outside Greia's allowed range");
    return this.#request("/system/update/package", { method: "POST", rawBody: file, contentType: SOFTWARE_UPDATE_MEDIA_TYPE });
  }
  buildUrl(path = "") { const normalized = path && !path.startsWith("/") ? `/${path}` : path; return `${this.origin}${this.apiBase}${normalized}`; }
  async #request(path, { method = "GET", body = undefined, rawBody = undefined, contentType = null, authenticated = true } = {}) {
    if (body !== undefined && rawBody !== undefined) throw new TypeError("request cannot contain both JSON and raw body data");
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (rawBody !== undefined) headers["Content-Type"] = contentType || "application/octet-stream";
    if (authenticated) { const token = this.credentialStore?.get(this.origin); if (token) headers.Authorization = `Bearer ${token}`; }
    let response;
    try { response = await this.fetchImpl(this.buildUrl(path), { method, credentials: "same-origin", headers, body: rawBody !== undefined ? rawBody : body === undefined ? undefined : JSON.stringify(body) }); }
    catch (error) { throw new ParentApiError("Could not reach this Greia", { code: "network_error", details: error }); }
    let payload = null; const responseContentType = response.headers?.get?.("content-type") ?? "";
    if (responseContentType.includes("application/json")) { try { payload = await response.json(); } catch (_) { payload = null; } }
    else { try { const text = await response.text(); payload = text ? { raw: text } : null; } catch (_) { payload = null; } }
    if (!response.ok) { const serverError = payload?.error; throw new ParentApiError(typeof serverError?.message === "string" ? serverError.message : `Greia request failed (${response.status})`, { status: response.status, code: typeof serverError?.code === "string" ? serverError.code : "http_error", details: payload }); }
    return payload;
  }
}

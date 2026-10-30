const KEY_PREFIX = "greia.parent.v1.credential:";
export class BrowserCredentialStore {
  constructor(storage = globalThis.localStorage) { this.storage = storage; }
  key(origin) { return `${KEY_PREFIX}${String(origin).replace(/\/$/, "")}`; }
  get(origin) { try { return this.storage?.getItem(this.key(origin)) || ""; } catch (_) { return ""; } }
  set(origin, token) { if (typeof token !== "string" || token.length < 16) throw new TypeError("credential is invalid"); this.storage?.setItem(this.key(origin), token); }
  remove(origin) { try { this.storage?.removeItem(this.key(origin)); } catch (_) {} }
}

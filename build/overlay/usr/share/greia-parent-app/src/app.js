import { ParentApiClient, ParentApiError } from "./api.js";
import { BrowserCredentialStore } from "./credential_store.js";
import { GreiaDeviceDiscoveryClient, DeviceScopedCredentialStore } from "./device_discovery.js";
import { ParentAppState } from "./state.js";
import { NAV_ITEMS, el, icon, button, currentRoute } from "./ui.js";
import { installHomeChildrenViews } from "./views_home_children.js";
import { installActivityViews } from "./views_activities.js";
import { installDeviceViews } from "./views_device.js";
import { installDeviceManagementLayout } from "./views_device_layout.js";
import { installSystemControlViews } from "./views_system_controls.js";
import { installAppHelpers } from "./views_helpers.js";

class GreiaParentApp {
  constructor({ credentialStore, discovery }) {
    this.credentialStore = credentialStore;
    this.discovery = discovery;
    this.api = null;
    this.state = null;
    this.unsubscribeState = null;
    this.discoveryMode = false;
    this.activeDevice = null;
    this.route = currentRoute();
    this.view = document.getElementById("view");
    this.flash = document.getElementById("flash");
    this.connectionLabel = document.getElementById("connection-label");
    this.connectionDot = document.getElementById("connection-dot");
    this.confirmDialog = document.getElementById("confirm-dialog");
    this.confirmResolver = null;
    this.flashTimer = null;
    this._buildNavigation();
    this._bindShell();
  }

  async start({ refreshDiscovery = false } = {}) {
    this._renderDiscoveryLoading();
    let discoveryResult;
    try {
      discoveryResult = await this.discovery.discover({ refresh: refreshDiscovery });
    } catch {
      this.discoveryMode = true;
      this._renderDiscoveryFailure();
      return;
    }

    if (discoveryResult !== null) {
      this.discoveryMode = true;
      const devices = discoveryResult.devices;
      const preferred = this.discovery.preferredOrigin();
      const preferredDevice = devices.find((device) => device.origin === preferred);
      if (preferredDevice) {
        await this._connectDiscoveredDevice(preferredDevice);
        return;
      }
      if (devices.length === 1) {
        await this._connectDiscoveredDevice(devices[0]);
        return;
      }
      this._renderDeviceChooser(devices);
      return;
    }

    this.discoveryMode = false;
    this.activeDevice = null;
    await this._bindApi(new ParentApiClient({ credentialStore: this.credentialStore }));
  }

  async _connectDiscoveredDevice(device) {
    this._renderConnectingDevice(device);
    try {
      const selected = await this.discovery.select(device.origin);
      const scopedCredentials = new DeviceScopedCredentialStore(this.credentialStore, selected.origin);
      this.activeDevice = selected;
      await this._bindApi(new ParentApiClient({
        origin: location.origin,
        credentialStore: scopedCredentials,
      }));
    } catch {
      this._renderDiscoveryFailure("That Greia disappeared before the connection was ready.");
    }
  }

  async _bindApi(api) {
    this.unsubscribeState?.();
    this.api = api;
    this.state = new ParentAppState(api);
    this.unsubscribeState = this.state.subscribe((snapshot) => this.render(snapshot));
    try {
      await this.state.initialize();
    } catch (error) {
      if (!error?.authenticationRequired) this.showFlash("This Greia did not answer.", "error");
    }
  }

  _buildNavigation() {
    for (const id of ["desktop-nav", "mobile-nav"]) {
      const host = document.getElementById(id);
      host.replaceChildren();
      for (const item of NAV_ITEMS) {
        const n = button(item.label, { iconName: item.icon, className: "nav-button" });
        n.dataset.route = item.id;
        n.addEventListener("click", () => this.navigate(item.id));
        host.append(n);
      }
    }
    const refresh = document.getElementById("refresh-button");
    refresh.replaceChildren(icon("refresh"), el("span", "", "Refresh"));
  }

  _bindShell() {
    window.addEventListener("hashchange", () => {
      this.route = currentRoute();
      if (this.state) this.render(this.state.snapshot);
      this._refreshWifiForDevice();
    });
    window.addEventListener("focus", () => this._refreshWifiForDevice());
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") this._refreshWifiForDevice();
    });
    document.getElementById("refresh-button").addEventListener("click", async () => {
      if (!this.state) {
        await this.start({ refreshDiscovery: true });
        return;
      }
      try {
        await this.state.refresh();
        this.showFlash("Greia refreshed.");
      } catch (error) {
        if (!error?.authenticationRequired) this.showFlash("This Greia did not answer.", "error");
      }
    });
    this.confirmDialog.addEventListener("close", () => {
      if (!this.confirmResolver) return;
      const resolver = this.confirmResolver;
      this.confirmResolver = null;
      resolver(this.confirmDialog.returnValue === "confirm");
    });
  }

  navigate(route) { location.hash = route; }

  _refreshWifiForDevice() {
    // The full snapshot is fetched once at startup. Entering the Device view
    // (or returning to the tab) after the device associated must re-read iwd;
    // otherwise an existing connection looks absent until a manual connect.
    if (!this.state || this.route !== "device") return;
    if (!this.state.capability("network.manage")) return;
    Promise.resolve(this.state.refreshWifi()).catch(() => {});
  }

  render(snapshot) {
    this._renderConnection(snapshot);
    for (const n of document.querySelectorAll(".nav-button")) {
      n.setAttribute("aria-current", n.dataset.route === this.route ? "page" : "false");
    }
    const info = NAV_ITEMS.find((item) => item.id === this.route) || NAV_ITEMS[0];
    document.getElementById("page-title").textContent = info.label;
    document.getElementById("page-subtitle").textContent = info.subtitle;
    document.getElementById("page-eyebrow").textContent = snapshot.meta?.device_name || this.activeDevice?.device_name || "Greia Parents";
    const pageActions = document.getElementById("page-actions");
    pageActions.replaceChildren();
    if (this.discoveryMode && this.activeDevice) {
      pageActions.append(button("Switch Greia", {
        className: "button secondary small",
        onClick: () => this._switchGreia(),
      }));
    }
    if (["booting", "loading"].includes(snapshot.phase)) {
      this.view.replaceChildren(this._loadingView());
      return;
    }
    if (snapshot.phase === "authentication") {
      this.view.replaceChildren(this._authenticationView(snapshot));
      return;
    }
    if (snapshot.phase === "error") {
      this.view.replaceChildren(this._errorView(snapshot.error));
      return;
    }
    const renderView = {
      home: () => this._home(snapshot),
      children: () => this._children(snapshot),
      activities: () => this._activities(snapshot),
      device: () => this._device(snapshot),
    }[this.route] || (() => this._home(snapshot));
    this.view.replaceChildren(renderView());
  }

  async _switchGreia() {
    this.unsubscribeState?.();
    this.unsubscribeState = null;
    this.state = null;
    this.api = null;
    this.activeDevice = null;
    this.discovery.remember("");
    await this.start({ refreshDiscovery: true });
  }

  _setDiscoveryChrome({ title, subtitle, connection }) {
    document.getElementById("page-eyebrow").textContent = "Greia Parents";
    document.getElementById("page-title").textContent = title;
    document.getElementById("page-subtitle").textContent = subtitle;
    document.getElementById("page-actions").replaceChildren();
    this.connectionDot.className = "connection-dot warning";
    this.connectionLabel.textContent = connection;
    for (const n of document.querySelectorAll(".nav-button")) n.setAttribute("aria-current", "false");
  }

  _renderDiscoveryLoading() {
    this._setDiscoveryChrome({
      title: "Finding your Greia",
      subtitle: "Looking for Greia computers on this network.",
      connection: "Searching…",
    });
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("search"));
    card.append(emblem, el("h2", "", "Looking for Greia computers"), el("p", "", "This normally takes a moment on a home network."));
    shell.append(card);
    this.view.replaceChildren(shell);
  }

  _renderConnectingDevice(device) {
    this._setDiscoveryChrome({
      title: "Connecting",
      subtitle: `Opening ${device.device_name}.`,
      connection: "Connecting…",
    });
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("device"));
    card.append(emblem, el("h2", "", device.device_name), el("p", "", "Checking access and loading Parent settings."));
    shell.append(card);
    this.view.replaceChildren(shell);
  }

  _renderDeviceChooser(devices) {
    this._setDiscoveryChrome({
      title: "Choose a Greia",
      subtitle: devices.length ? "Greia computers found on this network." : "No Greia computer was found on this network yet.",
      connection: devices.length ? `${devices.length} found` : "None found",
    });
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card device-picker");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon(devices.length ? "device" : "search"));
    card.append(emblem, el("h2", "", devices.length ? "Which Greia do you want to manage?" : "No Greia found"));
    if (!devices.length) {
      card.append(el("p", "", "Make sure the Greia computer is on and connected to the same local network."));
    } else {
      const list = el("div", "plain-list device-picker-list");
      for (const device of devices) {
        const row = el("div", "plain-row device-picker-row");
        const rowIcon = el("div", "row-icon");
        rowIcon.append(icon("device"));
        const copy = el("div", "row-copy");
        copy.append(el("strong", "", device.device_name), el("span", "", device.host));
        row.append(rowIcon, copy, button("Connect", {
          className: "button small",
          onClick: () => this._connectDiscoveredDevice(device),
        }));
        list.append(row);
      }
      card.append(list);
    }
    card.append(button("Search again", {
      iconName: "refresh",
      className: "button secondary full-width",
      onClick: () => this.start({ refreshDiscovery: true }),
    }));
    shell.append(card);
    this.view.replaceChildren(shell);
  }

  _renderDiscoveryFailure(message = "Greia device discovery could not run on this computer.") {
    this._setDiscoveryChrome({
      title: "Can't search the network",
      subtitle: "Greia Parents could not look for nearby Greia computers.",
      connection: "Discovery problem",
    });
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("device"));
    card.append(
      emblem,
      el("h2", "", "Couldn't find a Greia"),
      el("p", "", message),
      button("Search again", { iconName: "refresh", onClick: () => this.start({ refreshDiscovery: true }) }),
    );
    shell.append(card);
    this.view.replaceChildren(shell);
  }

  _renderConnection(snapshot) {
    this.connectionDot.className = "connection-dot";
    if (snapshot.phase === "ready") {
      this.connectionDot.classList.add("online");
      this.connectionLabel.textContent = snapshot.meta?.device_name || this.activeDevice?.device_name || "Connected";
    } else if (snapshot.phase === "authentication") {
      this.connectionDot.classList.add("warning");
      this.connectionLabel.textContent = "Password required";
    } else if (snapshot.phase === "error") {
      this.connectionDot.classList.add("offline");
      this.connectionLabel.textContent = "Connection problem";
    } else {
      this.connectionLabel.textContent = "Connecting…";
    }
  }

  _loadingView() {
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("refresh"));
    card.append(emblem, el("h2", "", "Opening your Greia"), el("p", "", "Loading children, Activities and device settings."));
    shell.append(card);
    return shell;
  }

  _errorView(error) {
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("device"));
    const message = ["network_error", "selected_greia_unreachable", "greia_device_not_selected"].includes(error?.code)
      ? "The selected Greia did not answer. It may be off or no longer on this network."
      : error?.message || "The Parent API did not respond.";
    card.append(emblem, el("h2", "", "This Greia isn't reachable right now"), el("p", "", message));
    const actions = el("div", "button-row");
    actions.append(button("Try again", { iconName: "refresh", onClick: async () => { try { await this.state?.refresh(); } catch {} } }));
    if (this.discoveryMode) {
      actions.append(button("Choose another Greia", { className: "button secondary", onClick: () => this._switchGreia() }));
    } else {
      actions.append(button("Forget connection", {
        className: "button secondary",
        onClick: () => { this.api?.forgetCredential?.(); this.start(); },
      }));
    }
    card.append(actions);
    shell.append(card);
    return shell;
  }

  _authenticationView(snapshot) {
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("shield"));
    card.append(
      emblem,
      el("h2", "", "Connect to this Greia"),
      el("p", "", `Enter the Greia password for ${snapshot.meta?.device_name || this.activeDevice?.device_name || "this Greia"}. New Greia systems start with the password “greia”.`),
    );
    const form = el("form", "form-grid");
    const name = this._textField("This device", "device_name", navigator.platform ? `${navigator.platform} browser` : "Parent browser");
    const password = this._textField("Greia password", "password", "", "password");
    name.classList.add("full");
    password.classList.add("full");
    const actions = el("div", "form-actions");
    const submit = button("Connect", { iconName: "key", type: "submit" });
    actions.append(submit);
    form.append(name, password, actions);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      submit.disabled = true;
      const data = new FormData(form);
      try {
        await this.api.connectWithPassword({
          password: String(data.get("password") || ""),
          deviceName: String(data.get("device_name") || "Parent browser"),
        });
        await this.state.refresh();
        this.showFlash("This browser is connected to Greia.");
      } catch (error) {
        this.showFlash(error?.message || "The Greia password was not accepted.", "error");
      } finally {
        submit.disabled = false;
      }
    });
    card.append(form);
    shell.append(card);
    return shell;
  }

  showFlash(message, kind = "ok") {
    this.flash.hidden = false;
    this.flash.className = `flash ${kind === "ok" ? "" : kind}`.trim();
    this.flash.textContent = message;
    clearTimeout(this.flashTimer);
    this.flashTimer = setTimeout(() => { this.flash.hidden = true; }, 4200);
  }

  confirm(title, message) {
    document.getElementById("confirm-title").textContent = title;
    document.getElementById("confirm-message").textContent = message;
    document.getElementById("confirm-icon").replaceChildren(icon("trash"));
    this.confirmDialog.returnValue = "cancel";
    this.confirmDialog.showModal();
    return new Promise((resolve) => { this.confirmResolver = resolve; });
  }
}

installHomeChildrenViews(GreiaParentApp.prototype);
installActivityViews(GreiaParentApp.prototype);
installDeviceViews(GreiaParentApp.prototype);
installSystemControlViews(GreiaParentApp.prototype);
installDeviceManagementLayout(GreiaParentApp.prototype);
installAppHelpers(GreiaParentApp.prototype);

const credentialStore = new BrowserCredentialStore();
const discovery = new GreiaDeviceDiscoveryClient();
const app = new GreiaParentApp({ credentialStore, discovery });
app.start().catch((error) => {
  if (!(error instanceof ParentApiError) || !error.authenticationRequired) console.error(error);
});
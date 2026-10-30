import { ParentApiClient, ParentApiError } from "./api.js";
import { BrowserCredentialStore } from "./credential_store.js";
import { GreiaDeviceDiscoveryClient, DeviceScopedCredentialStore } from "./device_discovery.js";
import { ParentAppState } from "./state.js";
import { NAV_ITEMS, el, icon, button, currentRoute } from "./ui.js";
import { setChromeLocale, tr, renderChromeTranslations } from "./localization.js";
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
    this._wifiRefreshRoute = null;
    this.view = document.getElementById("view");
    this.flash = document.getElementById("flash");
    this.connectionLabel = document.getElementById("connection-label");
    this.connectionDot = document.getElementById("connection-dot");
    this.confirmDialog = document.getElementById("confirm-dialog");
    this.confirmResolver = null;
    this.flashTimer = null;
    this._buildNavigation();
    renderChromeTranslations();
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
      this._renderDiscoveryFailure(tr("discovery.lost"));
    }
  }

  async _bindApi(api) {
    this.unsubscribeState?.();
    this.state?.dispose();
    this.api = api;
    this.state = new ParentAppState(api);
    this.unsubscribeState = this.state.subscribe((snapshot) => this.render(snapshot));
    try {
      await this.state.initialize();
    } catch (error) {
      if (!error?.authenticationRequired) this.showFlash(tr("shell.no_response"), "error");
    }
  }

  _buildNavigation() {
    for (const id of ["desktop-nav", "mobile-nav"]) {
      const host = document.getElementById(id);
      host.replaceChildren();
      for (const item of NAV_ITEMS) {
        const n = button(tr(item.labelKey), { iconName: item.icon, className: "nav-button" });
        n.dataset.route = item.id;
        n.addEventListener("click", () => this.navigate(item.id));
        host.append(n);
      }
    }
    const refresh = document.getElementById("refresh-button");
    refresh.replaceChildren(icon("refresh"), el("span", "", tr("shell.refresh")));
  }

  _bindShell() {
    window.addEventListener("hashchange", () => {
      this.route = currentRoute();
      if (this.state) this.render(this.state.snapshot);
    });
    document.getElementById("refresh-button").addEventListener("click", async () => {
      if (!this.state) {
        await this.start({ refreshDiscovery: true });
        return;
      }
      try {
        await this.state.refresh();
        this.showFlash(tr("shell.refreshed"));
      } catch (error) {
        if (!error?.authenticationRequired) this.showFlash(tr("shell.no_response"), "error");
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

  render(snapshot) {
    // The server selects the device's locale; the browser's preferred
    // supported language is used only before a device is authenticated.
    if (snapshot.language?.locale && setChromeLocale(snapshot.language.locale)) {
      this._buildNavigation();
      renderChromeTranslations();
    }
    this._renderConnection(snapshot);
    for (const n of document.querySelectorAll(".nav-button")) {
      n.setAttribute("aria-current", n.dataset.route === this.route ? "page" : "false");
    }
    const info = NAV_ITEMS.find((item) => item.id === this.route) || NAV_ITEMS[0];
    document.getElementById("page-title").textContent = tr(info.labelKey);
    document.getElementById("page-subtitle").textContent = tr(info.subtitleKey);
    document.getElementById("page-eyebrow").textContent = snapshot.meta?.device_name || this.activeDevice?.device_name || "Greia Parents";
    const pageActions = document.getElementById("page-actions");
    pageActions.replaceChildren();
    if (this.discoveryMode && this.activeDevice) {
      pageActions.append(button(tr("shell.switch"), {
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
    if (this.route === "device" && this._wifiRefreshRoute !== "device") {
      this._wifiRefreshRoute = "device";
      void this._refreshWifiForDevice();
    } else if (this.route !== "device") {
      this._wifiRefreshRoute = null;
    }
    const renderView = {
      home: () => this._home(snapshot),
      children: () => this._children(snapshot),
      activities: () => this._activities(snapshot),
      device: () => this._device(snapshot),
    }[this.route] || (() => this._home(snapshot));
    this.view.replaceChildren(renderView());
  }

  async _refreshWifiForDevice() {
    if (this.route !== "device") return;
    if (!this.state?.capability("network.manage")) return;
    try {
      await this.state.refreshWifi();
    } catch {
      // The state snapshot carries the feature error; keep the device view.
    }
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
      title: tr("discovery.title.search"),
      subtitle: tr("discovery.subtitle.search"),
      connection: tr("discovery.status.search"),
    });
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("search"));
    card.append(emblem, el("h2", "", tr("discovery.heading.search")), el("p", "", tr("discovery.note.search")));
    shell.append(card);
    this.view.replaceChildren(shell);
  }

  _renderConnectingDevice(device) {
    this._setDiscoveryChrome({
      title: tr("discovery.title.connecting"),
      subtitle: tr("discovery.subtitle.opening", { device: device.device_name }),
      connection: tr("shell.connecting"),
    });
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("device"));
    card.append(emblem, el("h2", "", device.device_name), el("p", "", tr("discovery.note.connecting")));
    shell.append(card);
    this.view.replaceChildren(shell);
  }

  _renderDeviceChooser(devices) {
    this._setDiscoveryChrome({
      title: tr("discovery.title.choose"),
      subtitle: devices.length ? tr("discovery.found") : tr("discovery.none"),
      connection: devices.length ? tr("discovery.count", { count: devices.length }) : tr("discovery.count.none"),
    });
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card device-picker");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon(devices.length ? "device" : "search"));
    card.append(emblem, el("h2", "", devices.length ? tr("discovery.heading.choose") : tr("discovery.heading.none")));
    if (!devices.length) {
      card.append(el("p", "", tr("discovery.note.none")));
    } else {
      const list = el("div", "plain-list device-picker-list");
      for (const device of devices) {
        const row = el("div", "plain-row device-picker-row");
        const rowIcon = el("div", "row-icon");
        rowIcon.append(icon("device"));
        const copy = el("div", "row-copy");
        copy.append(el("strong", "", device.device_name), el("span", "", device.host));
        row.append(rowIcon, copy, button(tr("discovery.connect"), {
          className: "button small",
          onClick: () => this._connectDiscoveredDevice(device),
        }));
        list.append(row);
      }
      card.append(list);
    }
    card.append(button(tr("discovery.search_again"), {
      iconName: "refresh",
      className: "button secondary full-width",
      onClick: () => this.start({ refreshDiscovery: true }),
    }));
    shell.append(card);
    this.view.replaceChildren(shell);
  }

  _renderDiscoveryFailure(message = tr("discovery.fail.default")) {
    this._setDiscoveryChrome({
      title: tr("discovery.fail.title"),
      subtitle: tr("discovery.fail.subtitle"),
      connection: tr("discovery.fail.status"),
    });
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("device"));
    card.append(
      emblem,
      el("h2", "", tr("discovery.fail.heading")),
      el("p", "", message),
      button(tr("discovery.search_again"), { iconName: "refresh", onClick: () => this.start({ refreshDiscovery: true }) }),
    );
    shell.append(card);
    this.view.replaceChildren(shell);
  }

  _renderConnection(snapshot) {
    this.connectionDot.className = "connection-dot";
    if (snapshot.phase === "ready") {
      this.connectionDot.classList.add("online");
      this.connectionLabel.textContent = snapshot.meta?.device_name || this.activeDevice?.device_name || tr("shell.connected");
    } else if (snapshot.phase === "authentication") {
      this.connectionDot.classList.add("warning");
      this.connectionLabel.textContent = tr("shell.password_required");
    } else if (snapshot.phase === "error") {
      this.connectionDot.classList.add("offline");
      this.connectionLabel.textContent = tr("shell.connection_problem");
    } else {
      this.connectionLabel.textContent = tr("shell.connecting");
    }
  }

  _loadingView() {
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("refresh"));
    card.append(emblem, el("h2", "", tr("session.loading.title")), el("p", "", tr("session.loading.note")));
    shell.append(card);
    return shell;
  }

  _errorView(error) {
    const shell = el("div", "pair-screen");
    const card = el("section", "pair-card");
    const emblem = el("div", "pair-emblem");
    emblem.append(icon("device"));
    const message = ["network_error", "selected_greia_unreachable", "greia_device_not_selected"].includes(error?.code)
      ? tr("session.error.unreachable")
      : error?.message || tr("session.error.generic");
    card.append(emblem, el("h2", "", tr("session.error.title")), el("p", "", message));
    const actions = el("div", "button-row");
    actions.append(button(tr("session.error.try_again"), { iconName: "refresh", onClick: async () => { try { await this.state?.refresh(); } catch {} } }));
    if (this.discoveryMode) {
      actions.append(button(tr("session.error.choose_another"), { className: "button secondary", onClick: () => this._switchGreia() }));
    } else {
      actions.append(button(tr("session.error.forget"), {
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
      el("h2", "", tr("auth.heading")),
      el("p", "", tr("auth.instructions", { device: snapshot.meta?.device_name || this.activeDevice?.device_name || tr("auth.this_device") })),
    );
    const form = el("form", "form-grid");
    const name = this._textField(tr("auth.device_label"), "device_name", navigator.platform ? `${navigator.platform} browser` : "Parent browser");
    const password = this._textField(tr("auth.password_label"), "password", "", "password");
    name.classList.add("full");
    password.classList.add("full");
    const actions = el("div", "form-actions");
    const submit = button(tr("discovery.connect"), { iconName: "key", type: "submit" });
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
        this.showFlash(tr("auth.connected"));
      } catch (error) {
        this.showFlash(error?.message || tr("auth.invalid"), "error");
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

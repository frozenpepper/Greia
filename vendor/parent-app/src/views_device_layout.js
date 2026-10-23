import { el, humanBytes, humanUptime, percent } from "./ui.js";
import { tr } from "./localization.js";

export function installDeviceManagementLayout(proto) {
  proto._device = function(snapshot) {
    const caps = snapshot.index?.capabilities || {};
    const root = el("div", "device-manager");

    const systemCards = [];
    const health = el("section", "card device-setting-card");
    health.append(this._cardHeader(tr("device.health"), tr("device.health.subtitle")));
    const diskUsed = Math.max(
      0,
      Number(snapshot.system?.disk_total_bytes || 0) - Number(snapshot.system?.disk_free_bytes || 0),
    );
    const memUsed = Math.max(
      0,
      Number(snapshot.system?.memory_total_bytes || 0) - Number(snapshot.system?.memory_available_bytes || 0),
    );
    health.append(
      this._meter(
        tr("device.storage"),
        diskUsed,
        snapshot.system?.disk_total_bytes,
        tr("device.storage.free", { amount: humanBytes(snapshot.system?.disk_free_bytes) }),
      ),
      this._meter(
        tr("device.memory"),
        memUsed,
        snapshot.system?.memory_total_bytes,
        tr("device.memory.available", { percent: percent(snapshot.system?.memory_available_bytes, snapshot.system?.memory_total_bytes) }),
      ),
      this._statusRow("device", tr("device.uptime"), humanUptime(snapshot.system?.uptime_seconds)),
    );
    systemCards.push(health);
    if (caps["system.update.read"] && snapshot.systemUpdate) systemCards.push(this._updateCard(snapshot));
    root.append(this._deviceGroup(tr("device.group.system"), tr("device.group.system.subtitle"), systemCards));

    const networkCards = [];
    if (caps["network.manage"]) networkCards.push(this._wifiCard(snapshot));
    else networkCards.push(this._wifiUnavailableCard());
    if (caps["settings.language"] && snapshot.language) networkCards.push(this._languageCard(snapshot));
    root.append(this._deviceGroup(tr("device.group.network"), tr("device.group.network.subtitle"), networkCards));

    const interactionCards = [];
    if (caps["settings.input"] || caps["settings.display"]) interactionCards.push(this._hardwareCard(snapshot));
    if (caps["settings.system_controls"]) interactionCards.push(this._systemControlsCard(snapshot));
    if (caps["settings.audio"] && snapshot.audio) interactionCards.push(this._audioCard(snapshot));
    if (interactionCards.length) root.append(this._deviceGroup(tr("device.group.interaction"), tr("device.group.interaction.subtitle"), interactionCards));

    const securityCards = [];
    if (caps["parent.password"]) securityCards.push(this._parentPasswordCard());
    if (caps["maintenance.ssh"]) securityCards.push(this._sshCard(snapshot));
    if (caps["paired_devices.manage"]) securityCards.push(this._devicesCard(snapshot));
    if (securityCards.length) root.append(this._deviceGroup(tr("device.group.security"), tr("device.group.security.subtitle"), securityCards));

    return root;
  };

  proto._wifiUnavailableCard = function() {
    const card = el("section", "card device-setting-card");
    card.append(
      this._cardHeader(tr("device.wifi.title"), tr("device.wifi.subtitle")),
      this._empty(
        "wifi",
        tr("device.wifi.unavailable"),
        tr("device.wifi.unavailable.note"),
      ),
    );
    return card;
  };

  proto._deviceGroup = function(title, subtitle, cards) {
    const group = el("section", "device-group");
    const heading = el("div", "device-group-heading");
    heading.append(el("h2", "", title), el("p", "", subtitle));
    const grid = el("div", "device-group-grid");
    for (const card of cards) {
      card.classList.remove("span-5", "span-7", "span-12");
      card.classList.add("device-setting-card");
      grid.append(card);
    }
    group.append(heading, grid);
    return group;
  };
}

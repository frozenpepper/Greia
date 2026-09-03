import { el, humanBytes, humanUptime, percent } from "./ui.js";

export function installDeviceManagementLayout(proto) {
  proto._device = function(snapshot) {
    const caps = snapshot.index?.capabilities || {};
    const root = el("div", "device-manager");

    const systemCards = [];
    const health = el("section", "card device-setting-card");
    health.append(this._cardHeader("System health", "Useful facts about this Greia"));
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
        "Storage",
        diskUsed,
        snapshot.system?.disk_total_bytes,
        `${humanBytes(snapshot.system?.disk_free_bytes)} free`,
      ),
      this._meter(
        "Memory",
        memUsed,
        snapshot.system?.memory_total_bytes,
        `${percent(snapshot.system?.memory_available_bytes, snapshot.system?.memory_total_bytes)}% available`,
      ),
      this._statusRow("device", "Uptime", humanUptime(snapshot.system?.uptime_seconds)),
    );
    systemCards.push(health);
    if (caps["system.update.read"] && snapshot.systemUpdate) systemCards.push(this._updateCard(snapshot));
    root.append(this._deviceGroup("System", "Health, storage and Greia software updates.", systemCards));

    const networkCards = [];
    if (caps["network.manage"]) networkCards.push(this._wifiCard(snapshot));
    else networkCards.push(this._wifiUnavailableCard());
    if (caps["settings.language"] && snapshot.language) networkCards.push(this._languageCard(snapshot));
    root.append(this._deviceGroup("Network & language", "Connect Greia and choose its everyday language.", networkCards));

    const interactionCards = [];
    if (caps["settings.input"] || caps["settings.display"]) interactionCards.push(this._hardwareCard(snapshot));
    if (caps["settings.system_controls"]) interactionCards.push(this._systemControlsCard(snapshot));
    if (caps["settings.audio"] && snapshot.audio) interactionCards.push(this._audioCard(snapshot));
    if (interactionCards.length) root.append(this._deviceGroup("Input, display & sound", "Mouse, touchpad, screen, speaker and microphone behaviour.", interactionCards));

    const securityCards = [];
    if (caps["parent.password"]) securityCards.push(this._parentPasswordCard());
    if (caps["maintenance.ssh"]) securityCards.push(this._sshCard(snapshot));
    if (caps["paired_devices.manage"]) securityCards.push(this._devicesCard(snapshot));
    if (securityCards.length) root.append(this._deviceGroup("Security & access", "Parent password, paired devices and maintenance access.", securityCards));

    return root;
  };

  proto._wifiUnavailableCard = function() {
    const card = el("section", "card device-setting-card");
    card.append(
      this._cardHeader("Wi-Fi", "Network setup on this device"),
      this._empty(
        "wifi",
        "Wi-Fi changes aren't available here",
        "Use Greia itself to change networks on this device. Parent only enables Wi-Fi controls when Greia can apply them directly.",
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

import { el, button, humanBytes, humanUptime, percent, MAX_UPDATE_BYTES } from "./ui.js";

export function installDeviceViews(proto) {
  proto._device = function(snapshot) {
    const root = el("div", "grid");
    const caps = snapshot.index?.capabilities || {};

    const health = el("section", "card span-5");
    health.append(this._cardHeader("System health", "A small set of useful facts"));
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
    root.append(health);

    if (caps["network.manage"]) root.append(this._wifiCard(snapshot));
    if (caps["settings.language"] && snapshot.language) root.append(this._languageCard(snapshot));
    if (caps["settings.input"] || caps["settings.display"]) root.append(this._hardwareCard(snapshot));
    if (caps["settings.audio"] && snapshot.audio) root.append(this._audioCard(snapshot));
    if (caps["parent.password"]) root.append(this._parentPasswordCard());
    if (caps["maintenance.ssh"]) root.append(this._sshCard(snapshot));
    if (caps["paired_devices.manage"]) root.append(this._devicesCard(snapshot));
    if (caps["system.update.read"] && snapshot.systemUpdate) root.append(this._updateCard(snapshot));
    return root;
  };

  proto._wifiCard = function(snapshot) {
    const card = el("section", "card span-7");
    card.append(this._cardHeader("Wi-Fi", "Connect Greia to a nearby network"));
    if (snapshot.featureErrors?.wifi) {
      card.append(
        this._empty(
          "wifi",
          "Wi-Fi isn't available right now",
          snapshot.featureErrors.wifi.message || "Try again later.",
        ),
      );
      return card;
    }

    const list = el("div", "wifi-list");
    for (const net of snapshot.wifi?.networks || []) {
      const row = el("div", "wifi-network");
      const signal = el("div", "signal");
      const bars = Math.max(1, Math.min(4, Math.round((Number(net.signal_dbm) + 100) / 15)));
      for (let i = 1; i <= 4; i += 1) {
        const bar = el("i");
        if (i <= bars) bar.classList.add("on");
        signal.append(bar);
      }
      const copy = el("div", "wifi-copy");
      copy.append(
        el("strong", "", net.ssid),
        el("span", "", net.security === "open" ? "Open network" : "Password protected"),
      );
      const connect = button("Connect", {
        className: "button small secondary",
        onClick: () => this._connectWifi(net),
      });
      row.append(signal, copy, connect);
      list.append(row);
    }
    if (!list.childElementCount) {
      list.append(this._empty("wifi", "No networks found", "Refresh Greia to scan again."));
    }
    card.append(list);
    return card;
  };

  proto._connectWifi = function(network) {
    const dialog = this._openDialog({
      title: `Connect to ${network.ssid}`,
      subtitle:
        network.security === "open"
          ? "This network does not use a password."
          : "Enter the Wi-Fi password. It is sent only to Greia.",
      iconName: "wifi",
    });
    const body = dialog.querySelector(".dialog-content");
    const form = el("form", "form-grid");
    const password = this._textField("Wi-Fi password", "passphrase", "", "password");
    if (network.security !== "open") form.append(password);
    const actions = el("div", "form-actions");
    const submit = button("Connect", { iconName: "wifi", type: "submit" });
    actions.append(submit);
    form.append(actions);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      submit.disabled = true;
      try {
        const data = new FormData(form);
        await this.api.connectWifi({
          ssid: network.ssid,
          passphrase: String(data.get("passphrase") || ""),
        });
        dialog.close();
        await this.state.refreshWifi();
        this.showFlash(`Connected to ${network.ssid}.`);
      } catch (error) {
        this.showFlash(error?.message || "Could not connect Wi-Fi.", "error");
      } finally {
        submit.disabled = false;
      }
    });
    body.append(form);
  };

  proto._languageCard = function(snapshot) {
    const card = el("section", "card span-5");
    card.append(this._cardHeader("Language", "Greia's default language"));
    const grid = el("div", "language-grid");
    for (const lang of snapshot.language?.languages || []) {
      const item = el(
        "button",
        `language-button${lang.locale === snapshot.language.locale ? " active" : ""}`,
      );
      item.type = "button";
      const flag = el("span", "language-flag", lang.flag || "🌐");
      const copy = el("span", "language-copy");
      copy.append(
        el("strong", "", lang.name || lang.locale),
        el("span", "", lang.native_name || lang.locale),
      );
      item.append(flag, copy);
      item.addEventListener("click", async () => {
        try {
          await this.api.updateLanguage(lang.locale);
          await this.state.refreshLanguage();
          this.showFlash(`Greia language changed to ${lang.name || lang.locale}.`);
        } catch (error) {
          this.showFlash(error?.message || "Could not change language.", "error");
        }
      });
      grid.append(item);
    }
    card.append(grid);
    return card;
  };

  proto._hardwareCard = function(snapshot) {
    const card = el("section", "card span-7");
    const desired = snapshot.hardware?.desired || {};
    const hasMicGain = Object.prototype.hasOwnProperty.call(desired, "mic_gain");
    card.append(
      this._cardHeader(
        hasMicGain ? "Input, microphone & display" : "Mouse, touchpad & display",
        hasMicGain
          ? "Everyday pointer, recording and screen settings"
          : "Everyday input and screen settings",
      ),
    );

    const form = el("form", "form-grid");
    const mouse = this._rangeField("Mouse speed", "mouse_speed", desired.mouse_speed ?? 0);
    const touch = this._rangeField("Touchpad speed", "touchpad_speed", desired.touchpad_speed ?? 0);
    const modes = [
      ["auto", "Automatic"],
      ...(snapshot.hardware?.display_modes || []).map((mode) => [mode.id, mode.id]),
    ];
    const resolution = this._selectField(
      "Resolution",
      "resolution",
      modes,
      desired.resolution || "auto",
    );

    form.append(mouse, touch);
    if (hasMicGain) {
      form.append(this._gainRangeField("Microphone level", "mic_gain", desired.mic_gain ?? 2.0));
    }
    form.append(
      resolution,
      this._checkField("Tap touchpad to click", "touchpad_tap", Boolean(desired.touchpad_tap)),
      this._checkField(
        "Natural scrolling",
        "natural_scrolling",
        Boolean(desired.natural_scrolling),
      ),
    );

    const actions = el("div", "form-actions");
    const reset = button("Restore defaults", { className: "button secondary" });
    const save = button("Apply settings", { iconName: "check", type: "submit" });
    actions.append(reset, save);
    form.append(actions);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      save.disabled = true;
      const data = new FormData(form);
      const payload = {
        mouse_speed: Number(data.get("mouse_speed")),
        touchpad_speed: Number(data.get("touchpad_speed")),
        resolution: String(data.get("resolution") || "auto"),
        touchpad_tap: data.get("touchpad_tap") === "on",
        natural_scrolling: data.get("natural_scrolling") === "on",
      };
      if (hasMicGain) payload.mic_gain = Number(data.get("mic_gain"));
      try {
        await this.api.updateHardware(payload);
        await this.state.refresh();
        this.showFlash(hasMicGain ? "Device settings applied." : "Input and display settings applied.");
      } catch (error) {
        this.showFlash(error?.message || "Could not apply settings.", "error");
      } finally {
        save.disabled = false;
      }
    });

    reset.addEventListener("click", async () => {
      const message = hasMicGain
        ? "Current pointer, microphone and resolution preferences will be reset."
        : "Current mouse, touchpad and resolution preferences will be reset.";
      if (!await this.confirm("Restore device defaults?", message)) return;
      try {
        await this.api.resetHardware();
        await this.state.refresh();
        this.showFlash("Defaults restored.");
      } catch (error) {
        this.showFlash(error?.message || "Could not restore defaults.", "error");
      }
    });

    card.append(form);
    return card;
  };

  proto._audioCard = function(snapshot) {
    const card = el("section", "card span-5");
    card.append(this._cardHeader("Microphone cleanup", "Greia can clean the microphone before Activities hear it"));
    if (snapshot.featureErrors?.audio) {
      card.append(
        this._empty(
          "device",
          "Microphone cleanup is unavailable",
          snapshot.featureErrors.audio.message || "Try refreshing Greia.",
        ),
      );
      return card;
    }

    const audio = snapshot.audio || {};
    const desired = audio.desired || {};
    const effective = audio.effective || {};
    const available = audio.available || {};
    const modeText = effective.microphone_processing_mode === "advanced"
      ? "Enhanced cleanup active"
      : effective.microphone_processing_mode === "lightweight"
        ? "Lightweight cleanup active"
        : "Using the raw microphone";
    const detail = effective.fallback_reason
      ? "The requested processor is not available, so Greia is using the safest available fallback."
      : "Changes take effect the next time an Activity opens the microphone.";
    card.append(this._statusRow("device", modeText, detail));

    const form = el("form", "form-grid");
    const processing = this._checkField(
      "Improve microphone sound",
      "microphone_processing_enabled",
      Boolean(desired.microphone_processing_enabled),
    );
    form.append(processing);

    const explanation = el(
      "div",
      "list-subtitle full",
      "Uses Greia's very lightweight microphone cleanup by default. Turn this off to give Activities the raw microphone signal.",
    );
    form.append(explanation);

    if (available.advanced) {
      form.append(
        this._checkField(
          "Enhanced noise reduction",
          "advanced_noise_reduction",
          Boolean(desired.advanced_noise_reduction),
        ),
        el(
          "div",
          "list-subtitle full",
          "Uses more processor power. Enable it only if this Greia handles it comfortably; Greia never turns it on automatically.",
        ),
      );
    }

    const actions = el("div", "form-actions");
    const reset = button("Restore microphone defaults", { className: "button secondary" });
    const save = button("Apply microphone settings", { iconName: "check", type: "submit" });
    actions.append(reset, save);
    form.append(actions);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      save.disabled = true;
      const data = new FormData(form);
      const payload = {
        microphone_processing_enabled: data.get("microphone_processing_enabled") === "on",
      };
      if (available.advanced) {
        payload.advanced_noise_reduction = data.get("advanced_noise_reduction") === "on";
      }
      try {
        await this.api.updateAudio(payload);
        await this.state.refreshAudio();
        this.showFlash("Microphone settings applied.");
      } catch (error) {
        this.showFlash(error?.message || "Could not apply microphone settings.", "error");
      } finally {
        save.disabled = false;
      }
    });

    reset.addEventListener("click", async () => {
      if (!await this.confirm(
        "Restore microphone defaults?",
        "Lightweight microphone cleanup will be enabled and enhanced cleanup will be turned off.",
      )) return;
      try {
        await this.api.resetAudio();
        await this.state.refreshAudio();
        this.showFlash("Microphone defaults restored.");
      } catch (error) {
        this.showFlash(error?.message || "Could not restore microphone defaults.", "error");
      }
    });

    card.append(form);
    return card;
  };

  proto._parentPasswordCard = function() {
    const card = el("section", "card span-5");
    card.append(this._cardHeader("Parent password", "Change the main Parent password"));
    const form = el("form", "form-grid");
    const current = this._textField("Current password", "current_password", "", "password");
    const fresh = this._textField("New password", "new_password", "", "password");
    current.classList.add("full");
    fresh.classList.add("full");
    const actions = el("div", "form-actions");
    const save = button("Change password", { iconName: "key", type: "submit" });
    actions.append(save);
    form.append(current, fresh, actions);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      save.disabled = true;
      const data = new FormData(form);
      try {
        await this.api.changeParentPassword({
          currentPassword: String(data.get("current_password") || ""),
          newPassword: String(data.get("new_password") || ""),
        });
        form.reset();
        this.showFlash("Parent password changed.");
      } catch (error) {
        this.showFlash(error?.message || "Could not change Parent password.", "error");
      } finally {
        save.disabled = false;
      }
    });
    card.append(form);
    return card;
  };

  proto._sshCard = function(snapshot) {
    const card = el("section", "card span-5");
    card.append(this._cardHeader("SSH maintenance", "Remote shell access for deliberate maintenance"));
    if (snapshot.featureErrors?.ssh) {
      card.append(
        this._empty(
          "terminal",
          "SSH status is unavailable",
          snapshot.featureErrors.ssh.message || "Try refreshing Greia.",
        ),
      );
      return card;
    }
    const active = Boolean(snapshot.ssh?.active || snapshot.ssh?.enabled);
    card.append(
      this._statusRow(
        "terminal",
        active ? "SSH is on" : "SSH is off",
        active
          ? snapshot.ssh?.connection_string || "Maintenance access enabled"
          : "Normal Greia use does not need SSH",
      ),
    );
    const action = button(active ? "Turn SSH off" : "Turn SSH on", {
      iconName: "terminal",
      className: active ? "button danger" : "button secondary",
    });
    action.addEventListener("click", async () => {
      if (active && !await this.confirm("Turn SSH off?", "Existing remote maintenance sessions may end.")) {
        return;
      }
      action.disabled = true;
      try {
        await this.api.updateSsh({ enabled: !active });
        await this.state.refreshSsh();
        this.showFlash(!active ? "SSH maintenance enabled." : "SSH maintenance disabled.");
      } catch (error) {
        this.showFlash(error?.message || "Could not change SSH maintenance.", "error");
      } finally {
        action.disabled = false;
      }
    });
    card.append(action);
    return card;
  };

  proto._devicesCard = function(snapshot) {
    const card = el("section", "card span-7");
    card.append(this._cardHeader("Parent devices", "Browsers and devices allowed to manage this Greia"));
    const list = el("div", "list");
    for (const device of snapshot.devices || []) {
      const row = el("div", "list-item");
      const copy = el("div", "list-main");
      copy.append(this._avatar({ avatar_id: "robot" }));
      const text = el("div");
      text.append(
        el("div", "list-title", device.display_name),
        el(
          "div",
          "list-subtitle",
          device.created_at ? `Paired ${new Date(device.created_at).toLocaleDateString()}` : "Paired device",
        ),
      );
      copy.append(text);
      const revoke = button("Revoke", {
        className: "button small danger",
        onClick: async () => {
          if (!await this.confirm(`Revoke ${device.display_name}?`, "That device will need to pair again.")) {
            return;
          }
          try {
            await this.api.revokeDevice(device.device_id);
            await this.state.refresh();
            this.showFlash("Parent device revoked.");
          } catch (error) {
            this.showFlash(error?.message || "Could not revoke device.", "error");
          }
        },
      });
      row.append(copy, revoke);
      list.append(row);
    }
    if (!list.childElementCount) {
      list.append(this._empty("shield", "No paired devices listed", "Pairing records will appear here."));
    }
    card.append(list);
    return card;
  };

  proto._updateCard = function(snapshot) {
    const card = el("section", "card span-12");
    card.append(this._cardHeader("Greia OS update", "System update status"));
    const status = snapshot.systemUpdate || {};
    const text =
      status.state === "received" && status.release?.version
        ? `Update ${status.release.version} received.`
        : status.activation_available
          ? "Updates are available on this Greia."
          : "No system update is currently staged on this Greia.";
    card.append(this._statusRow("refresh", "Update status", text));
    if (snapshot.index?.capabilities?.["system.update.upload"]) {
      const form = el("form", "install-row");
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".greiaupdate,application/vnd.greia.system-update+zip,application/zip";
      const submit = button("Send update", { iconName: "upload", type: "submit" });
      form.append(input, submit);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const file = input.files?.[0];
        if (!file) return this.showFlash("Choose a .greiaupdate file first.", "error");
        if (file.size <= 0 || file.size > MAX_UPDATE_BYTES) {
          return this.showFlash("The update file is outside Greia's allowed size.", "error");
        }
        submit.disabled = true;
        try {
          await this.api.uploadSystemUpdate(file);
          form.reset();
          await this.state.refresh();
          this.showFlash("Update sent to Greia.");
        } catch (error) {
          this.showFlash(error?.message || "Could not send update.", "error");
        } finally {
          submit.disabled = false;
        }
      });
      card.append(form);
    }
    return card;
  };

  proto._meter = function(label, used, total, detail) {
    const wrap = el("div", "meter-row");
    const head = el("div", "meter-label");
    const track = el("div", "meter-track");
    const fill = el("span");
    head.append(el("strong", "", label), el("span", "", detail));
    fill.style.width = `${percent(used, total)}%`;
    track.append(fill);
    wrap.append(head, track);
    return wrap;
  };

  proto._rangeField = function(label, name, value) {
    return this._boundedRangeField(label, name, value, {
      min: -1,
      max: 1,
      step: 0.25,
      format: (number) => number.toFixed(2),
    });
  };

  proto._gainRangeField = function(label, name, value) {
    return this._boundedRangeField(label, name, value, {
      min: 0.5,
      max: 4,
      step: 0.25,
      format: (number) => `${Math.round(number * 100)}% · ${number.toFixed(2)}×`,
    });
  };

  proto._boundedRangeField = function(label, name, value, { min, max, step, format }) {
    const wrap = el("div", "field");
    const labelNode = el("label", "", label);
    const line = el("div", "range-line");
    const input = document.createElement("input");
    const current = Number(value);
    const output = el("span", "range-value", format(current));
    input.type = "range";
    input.name = name;
    input.min = String(min);
    input.max = String(max);
    input.step = String(step);
    input.value = String(current);
    input.addEventListener("input", () => {
      output.textContent = format(Number(input.value));
    });
    line.append(input, output);
    wrap.append(labelNode, line);
    return wrap;
  };
}

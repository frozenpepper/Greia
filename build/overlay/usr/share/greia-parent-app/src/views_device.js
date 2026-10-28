import { el, button, humanBytes, humanUptime, percent, MAX_UPDATE_BYTES, MAX_SOFTWARE_UPDATE_BYTES } from "./ui.js";
import { tr, getChromeLocale } from "./localization.js";

export function installDeviceViews(proto) {
  proto._device = function(snapshot) {
    const root = el("div", "grid");
    const caps = snapshot.index?.capabilities || {};

    const health = el("section", "card span-5");
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
        tr("device.storage.free",{amount:humanBytes(snapshot.system?.disk_free_bytes)}),
      ),
      this._meter(
        tr("device.memory"),
        memUsed,
        snapshot.system?.memory_total_bytes,
        tr("device.memory.available",{percent:percent(snapshot.system?.memory_available_bytes,snapshot.system?.memory_total_bytes)}),
      ),
      this._statusRow("device", tr("device.uptime"), humanUptime(snapshot.system?.uptime_seconds)),
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
    card.append(this._cardHeader("Wi-Fi", tr("device.wifi.connect_help")));
    const connected = String(snapshot.wifi?.connected_ssid || "").trim();
    card.append(this._statusRow(
      "wifi",
      connected ? tr("device.wifi.connected_state", { name: connected }) : tr("device.wifi.not_connected_state"),
      "",
    ));
    if (snapshot.featureErrors?.wifi) {
      card.append(
        this._empty(
          "wifi",
          tr("device.wifi.no_service"),
          snapshot.featureErrors.wifi.message || tr("device.wifi.retry"),
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
        el("span", "", net.security === "open" ? tr("device.wifi.open_network") : tr("device.wifi.password_protected")),
      );
      const connect = button(tr("device.wifi.connect"), {
        className: "button small secondary",
        onClick: () => this._connectWifi(net),
      });
      row.append(signal, copy, connect);
      list.append(row);
    }
    if (!list.childElementCount) {
      list.append(this._empty("wifi", tr("device.wifi.none"), tr("device.wifi.scan_again")));
    }
    card.append(list);
    return card;
  };

  proto._connectWifi = function(network) {
    const dialog = this._openDialog({
      title: tr("device.wifi.connect_to",{name:network.ssid}),
      subtitle:
        network.security === "open"
          ? tr("device.wifi.open_help")
          : tr("device.wifi.password_help"),
      iconName: "wifi",
    });
    const body = dialog.querySelector(".dialog-content");
    const form = el("form", "form-grid");
    const password = this._textField(tr("device.wifi.password"), "passphrase", "", "password");
    if (network.security !== "open") form.append(password);
    const actions = el("div", "form-actions");
    const submit = button(tr("device.wifi.connect"), { iconName: "wifi", type: "submit" });
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
        this.showFlash(tr("device.wifi.connected",{name:network.ssid}));
      } catch (error) {
        this.showFlash(error?.message || tr("device.wifi.failed"), "error");
      } finally {
        submit.disabled = false;
      }
    });
    body.append(form);
  };

  proto._languageCard = function(snapshot) {
    const card = el("section", "card span-5");
    card.append(this._cardHeader(tr("device.language.title"), tr("device.language.description")));
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
          this.showFlash(tr("device.language.changed", { language: lang.native_name || lang.name || lang.locale }));
        } catch (error) {
          this.showFlash(error?.message || tr("device.language.failed"), "error");
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
        hasMicGain ? tr("device.hardware.full") : tr("device.hardware.simple"),
        hasMicGain
          ? tr("device.hardware.full_help")
          : tr("device.hardware.simple_help"),
      ),
    );

    const form = el("form", "form-grid");
    const mouse = this._rangeField(tr("device.hardware.mouse"), "mouse_speed", desired.mouse_speed ?? 0);
    const touch = this._rangeField(tr("device.hardware.touchpad"), "touchpad_speed", desired.touchpad_speed ?? 0);
    const modes = [
      ["auto", tr("device.hardware.auto")],
      ...(snapshot.hardware?.display_modes || []).map((mode) => [mode.id, mode.id]),
    ];
    const resolution = this._selectField(
      tr("device.hardware.resolution"),
      "resolution",
      modes,
      desired.resolution || "auto",
    );

    form.append(mouse, touch);
    if (hasMicGain) {
      form.append(this._gainRangeField(tr("device.hardware.microphone"), "mic_gain", desired.mic_gain ?? 2.0));
    }
    form.append(
      resolution,
      this._checkField(tr("device.hardware.tap"), "touchpad_tap", Boolean(desired.touchpad_tap)),
      this._checkField(
        tr("device.hardware.scroll"),
        "natural_scrolling",
        Boolean(desired.natural_scrolling),
      ),
    );

    const actions = el("div", "form-actions");
    const reset = button(tr("device.hardware.defaults"), { className: "button secondary" });
    const save = button(tr("device.hardware.apply"), { iconName: "check", type: "submit" });
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
        this.showFlash(hasMicGain ? tr("device.hardware.applied_full") : tr("device.hardware.applied_simple"));
      } catch (error) {
        this.showFlash(error?.message || tr("device.hardware.failed"), "error");
      } finally {
        save.disabled = false;
      }
    });

    reset.addEventListener("click", async () => {
      const message = hasMicGain
        ? tr("device.hardware.reset_full")
        : tr("device.hardware.reset_simple");
      if (!await this.confirm(tr("device.hardware.reset_confirm"), message)) return;
      try {
        await this.api.resetHardware();
        await this.state.refresh();
        this.showFlash(tr("device.hardware.restored"));
      } catch (error) {
        this.showFlash(error?.message || tr("device.hardware.restore_failed"), "error");
      }
    });

    card.append(form);
    return card;
  };

  proto._audioCard = function(snapshot) {
    const card = el("section", "card span-5");
    card.append(this._cardHeader(tr("device.mic.title"), tr("device.mic.subtitle")));
    if (snapshot.featureErrors?.audio) {
      card.append(
        this._empty(
          "device",
          tr("device.mic.unavailable"),
          snapshot.featureErrors.audio.message || tr("device.sound.try_again"),
        ),
      );
      return card;
    }

    const audio = snapshot.audio || {};
    const desired = audio.desired || {};
    const effective = audio.effective || {};
    const available = audio.available || {};
    const modeText = effective.microphone_processing_mode === "advanced"
      ? tr("device.mic.active_advanced")
      : effective.microphone_processing_mode === "lightweight"
        ? tr("device.mic.active_light")
        : tr("device.mic.raw");
    const detail = effective.fallback_reason
      ? tr("device.mic.fallback")
      : tr("device.mic.next_open");
    card.append(this._statusRow("device", modeText, detail));

    const form = el("form", "form-grid");
    const processing = this._checkField(
      tr("device.mic.improve"),
      "microphone_processing_enabled",
      Boolean(desired.microphone_processing_enabled),
    );
    form.append(processing);

    const explanation = el(
      "div",
      "list-subtitle full",
      tr("device.mic.help"),
    );
    form.append(explanation);

    if (available.advanced) {
      form.append(
        this._checkField(
          tr("device.mic.advanced"),
          "advanced_noise_reduction",
          Boolean(desired.advanced_noise_reduction),
        ),
        el(
          "div",
          "list-subtitle full",
          tr("device.mic.advanced_help"),
        ),
      );
    }

    const actions = el("div", "form-actions");
    const reset = button(tr("device.mic.restore"), { className: "button secondary" });
    const save = button(tr("device.mic.apply"), { iconName: "check", type: "submit" });
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
        this.showFlash(tr("device.mic.applied"));
      } catch (error) {
        this.showFlash(error?.message || tr("device.mic.apply_failed"), "error");
      } finally {
        save.disabled = false;
      }
    });

    reset.addEventListener("click", async () => {
      if (!await this.confirm(
        tr("device.mic.restore_confirm"),
        tr("device.mic.restore_warning"),
      )) return;
      try {
        await this.api.resetAudio();
        await this.state.refreshAudio();
        this.showFlash(tr("device.mic.restored"));
      } catch (error) {
        this.showFlash(error?.message || tr("device.mic.restore_failed"), "error");
      }
    });

    card.append(form);
    return card;
  };

  proto._parentPasswordCard = function() {
    const card = el("section", "card span-5");
    card.append(this._cardHeader(tr("device.parentpw.title"), tr("device.parentpw.subtitle")));
    const form = el("form", "form-grid");
    const current = this._textField(tr("device.parentpw.current"), "current_password", "", "password");
    const fresh = this._textField(tr("device.parentpw.new"), "new_password", "", "password");
    current.classList.add("full");
    fresh.classList.add("full");
    const actions = el("div", "form-actions");
    const save = button(tr("device.parentpw.change"), { iconName: "key", type: "submit" });
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
        this.showFlash(tr("device.parentpw.changed"));
      } catch (error) {
        this.showFlash(error?.message || tr("device.parentpw.failed"), "error");
      } finally {
        save.disabled = false;
      }
    });
    card.append(form);
    return card;
  };

  proto._sshCard = function(snapshot) {
    const card = el("section", "card span-5");
    card.append(this._cardHeader(tr("device.ssh.title"), tr("device.ssh.subtitle")));
    if (snapshot.featureErrors?.ssh) {
      card.append(
        this._empty(
          "terminal",
          tr("device.ssh.unavailable"),
          snapshot.featureErrors.ssh.message || tr("device.sound.try_again"),
        ),
      );
      return card;
    }
    const active = Boolean(snapshot.ssh?.active || snapshot.ssh?.enabled);
    card.append(
      this._statusRow(
        "terminal",
        active ? tr("device.ssh.on") : tr("device.ssh.off"),
        active
          ? snapshot.ssh?.connection_string || tr("device.ssh.enabled_description")
          : tr("device.ssh.disabled_description"),
      ),
    );
    const action = button(active ? tr("device.ssh.turn_off") : tr("device.ssh.turn_on"), {
      iconName: "terminal",
      className: active ? "button danger" : "button secondary",
    });
    action.addEventListener("click", async () => {
      if (active && !await this.confirm(tr("device.ssh.turn_off_confirm"), tr("device.ssh.disconnect_warning"))) {
        return;
      }
      action.disabled = true;
      try {
        await this.api.updateSsh({ enabled: !active });
        await this.state.refreshSsh();
        this.showFlash(!active ? tr("device.ssh.enabled") : tr("device.ssh.disabled"));
      } catch (error) {
        this.showFlash(error?.message || tr("device.ssh.failed"), "error");
      } finally {
        action.disabled = false;
      }
    });
    card.append(action);
    return card;
  };

  proto._devicesCard = function(snapshot) {
    const card = el("section", "card span-7");
    card.append(this._cardHeader(tr("device.paired.title"), tr("device.paired.subtitle")));
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
          device.created_at ? tr("device.paired.date",{date:new Date(device.created_at).toLocaleDateString(getChromeLocale())}) : tr("device.paired.generic"),
        ),
      );
      copy.append(text);
      const revoke = button(tr("device.paired.revoke"), {
        className: "button small danger",
        onClick: async () => {
          if (!await this.confirm(tr("device.paired.revoke_confirm",{name:device.display_name}), tr("device.paired.revoke_warning"))) {
            return;
          }
          try {
            await this.api.revokeDevice(device.device_id);
            await this.state.refresh();
            this.showFlash(tr("device.paired.revoked"));
          } catch (error) {
            this.showFlash(error?.message || tr("device.paired.failed"), "error");
          }
        },
      });
      row.append(copy, revoke);
      list.append(row);
    }
    if (!list.childElementCount) {
      list.append(this._empty("shield", tr("device.paired.none"), tr("device.paired.none_help")));
    }
    card.append(list);
    return card;
  };

  proto._updateCard = function(snapshot) {
    const card = el("section", "card span-12");
    card.append(this._cardHeader(tr("device.update.title"), tr("device.update.subtitle")));
    const status = snapshot.systemUpdate || {};
    const delivery = status.delivery || {};
    const job = delivery.job;
    const softwareUpdate = status.software_update || {};
    const softwareJob = softwareUpdate.job;
    const capabilities = snapshot.index?.capabilities || {};
    const jobState = typeof job?.state === "string" ? job.state : "";
    const softwareJobState = typeof softwareJob?.state === "string" ? softwareJob.state : "";
    const softwareBusy = Boolean(softwareJob && !["applied", "rolled_back", "failed"].includes(softwareJobState));
    const text = jobState
      ? tr(`device.update.job.${jobState}`)
      : status.state === "received" && status.release?.version
        ? tr("device.update.received", { version: status.release.version })
        : status.activation_available
          ? tr("device.update.available")
          : tr("device.update.none");
    card.append(this._statusRow("refresh", tr("device.update.status"), text));
    if (job?.operation === "prepare" && Number(job.total_bytes) > 0) {
      const total = Number(job.total_bytes);
      const downloaded = Math.max(0, Math.min(total, Number(job.downloaded_bytes) || 0));
      const progress = document.createElement("progress");
      progress.className = "system-update-progress";
      progress.max = 100;
      progress.value = Math.round((downloaded / total) * 100);
      progress.setAttribute("aria-label", tr("device.update.progress", { percent: progress.value }));
      card.append(progress, el("p", "muted", tr("device.update.bytes", { downloaded: humanBytes(downloaded), total: humanBytes(total) })));
    }
    if (job?.error_message) card.append(el("p", "form-error", job.error_message));
    if (status.activation_available === false && status.activation_reason) {
      card.append(el("p", "muted", status.activation_reason));
    }

    if (softwareJobState) {
      const softwareLabel = tr(`device.update.package.${softwareJobState}`);
      const versionLabel = typeof softwareJob.version === "string" && softwareJob.version ? ` · ${softwareJob.version}` : "";
      card.append(this._statusRow("upload", tr("device.update.package.title"), `${softwareLabel}${versionLabel}`));
      const total = Number(softwareJob.package_bytes);
      const received = Math.max(0, Math.min(total, Number(softwareJob.received_bytes) || 0));
      if (total > 0) {
        const progress = document.createElement("progress");
        progress.className = "system-update-progress";
        progress.max = 100;
        progress.value = Math.round((received / total) * 100);
        progress.setAttribute("aria-label", tr("device.update.package.received"));
        card.append(progress, el("p", "muted", tr("device.update.bytes", { downloaded: humanBytes(received), total: humanBytes(total) })));
      }
      if (softwareJob.error_message) card.append(el("p", "form-error", softwareJob.error_message));
      if (softwareBusy) {
        card.append(el("p", "muted", tr("device.update.package.help")));
      }
    }
    if (softwareUpdate.available === false && softwareUpdate.reason) {
      card.append(el("p", "muted", softwareUpdate.reason));
    }

    const activeJob = ["checking", "queued", "downloading", "receiving", "verifying", "staging", "restart_pending"].includes(jobState) || softwareBusy;
    const updateActions = el("div", "actions system-update-actions");
    if (capabilities["system.update.check"] && status.check_available === true) {
      const check = button(tr("device.update.check"), { iconName: "refresh", className: "button secondary" });
      check.disabled = activeJob;
      check.addEventListener("click", () => this._runSystemUpdateAction(check, () => this.state.checkSystemUpdate()));
      updateActions.append(check);
    }
    const releases = Array.isArray(delivery.catalog?.releases) ? delivery.catalog.releases.slice(0, 12) : [];
    if (capabilities["system.update.prepare"] && status.prepare_available === true) {
      for (const release of releases) {
        if (typeof release?.release_id !== "string" || !release.release_id) continue;
        const prepare = button(tr("device.update.prepare", { version: release.version || release.release_id }), { iconName: "download", className: "button secondary" });
        prepare.disabled = activeJob;
        prepare.addEventListener("click", () => this._runSystemUpdateAction(prepare, () => this.state.prepareSystemUpdate(release.release_id)));
        updateActions.append(prepare);
      }
    }
    if (capabilities["system.update.restart"] && status.restart_available === true && jobState === "ready_to_restart") {
      const restart = button(tr("device.update.restart"), { iconName: "refresh" });
      restart.addEventListener("click", async () => {
        if (!await this.confirm(tr("device.update.restart_confirm_title"), tr("device.update.restart_confirm_body"))) return;
        await this._runSystemUpdateAction(restart, () => this.state.restartSystemUpdate());
      });
      updateActions.append(restart);
    }
    if (capabilities["system.update.package.install"] && softwareUpdate.available === true && softwareUpdate.restart_available === true && softwareJobState === "ready_to_restart") {
      const restartPackage = button(tr("device.update.restart"), { iconName: "refresh" });
      restartPackage.addEventListener("click", async () => {
        if (!await this.confirm(tr("device.update.restart_confirm_title"), tr("device.update.restart_confirm_body"))) return;
        await this._runSystemUpdateAction(restartPackage, () => this.state.restartSoftwareUpdatePackage());
      });
      updateActions.append(restartPackage);
    }
    if (updateActions.childElementCount) card.append(updateActions);

    if (snapshot.index?.capabilities?.["system.update.upload"]) {
      const form = el("form", "install-row");
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".greiaupdate,application/vnd.greia.system-update+zip,application/zip";
      const submit = button(tr("device.update.send"), { iconName: "upload", type: "submit" });
      form.append(input, submit);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const file = input.files?.[0];
        if (!file) return this.showFlash(tr("device.update.choose"), "error");
        if (file.size <= 0 || file.size > MAX_UPDATE_BYTES) {
          return this.showFlash(tr("device.update.size"), "error");
        }
        submit.disabled = true;
        try {
          await this.api.uploadSystemUpdate(file);
          form.reset();
          await this.state.refresh();
          this.showFlash(tr("device.update.sent"));
        } catch (error) {
          this.showFlash(error?.message || tr("device.update.failed"), "error");
        } finally {
          submit.disabled = false;
        }
      });
      card.append(form);
    }
    if (capabilities["system.update.package.install"] && softwareUpdate.available === true) {
      const packageSection = el("div", "install-section");
      packageSection.append(el("h3", "", tr("device.update.package.title")), el("p", "muted", tr("device.update.package.help")));
      const form = el("form", "install-row");
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".greia_update,application/vnd.greia.software-update+zip";
      const submit = button(tr("device.update.package.send"), { iconName: "upload", type: "submit" });
      submit.disabled = activeJob;
      form.append(input, submit);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const file = input.files?.[0];
        if (!file) return this.showFlash(tr("device.update.package.choose"), "error");
        if (!file.name.toLowerCase().endsWith(".greia_update") || file.size <= 0 || file.size > MAX_SOFTWARE_UPDATE_BYTES) {
          return this.showFlash(tr("device.update.size"), "error");
        }
        if (activeJob) return this.showFlash(tr("device.update.failed"), "error");
        submit.disabled = true;
        try {
          await this.state.uploadSoftwareUpdatePackage(file);
          form.reset();
          this.showFlash(tr("device.update.package.sent"));
        } catch (error) {
          this.showFlash(error?.message || tr("device.update.failed"), "error");
        } finally {
          submit.disabled = false;
        }
      });
      packageSection.append(form);
      card.append(packageSection);
    }
    return card;
  };

  proto._runSystemUpdateAction = async function(control, action) {
    control.disabled = true;
    try {
      await action();
    } catch (error) {
      this.showFlash(error?.message || tr("device.update.failed"), "error");
    } finally {
      control.disabled = false;
    }
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

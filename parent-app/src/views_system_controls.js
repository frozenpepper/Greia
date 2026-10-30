import { el, button } from "./ui.js";
import { tr } from "./localization.js";

export function installSystemControlViews(proto) {
  proto._systemControlsCard = function(snapshot) {
    const card = el("section", "card span-5");
    card.append(this._cardHeader(tr("device.sound.title"), tr("device.sound.subtitle")));

    if (snapshot.featureErrors?.systemControls) {
      card.append(
        this._empty(
          "device",
          tr("device.sound.unavailable"),
          snapshot.featureErrors.systemControls.message || tr("device.sound.try_again"),
        ),
      );
      return card;
    }

    const controls = snapshot.systemControls || {};
    const volume = Number.isInteger(controls.volume_percent)
      ? Math.max(0, Math.min(100, controls.volume_percent))
      : 70;
    const muted = Boolean(controls.muted);

    card.append(
      this._statusRow(
        "device",
        muted ? tr("device.sound.muted") : tr("device.sound.volume", { percent: volume }),
        tr("device.sound.keys"),
      ),
    );

    const form = el("form", "form-grid");
    const volumeField = this._boundedRangeField(tr("device.sound.volume_label"), "volume_percent", volume, {
      min: 0,
      max: 100,
      step: 5,
      format: (number) => `${Math.round(number)}%`,
    });
    volumeField.classList.add("full");
    const mutedField = this._checkField(tr("device.sound.mute"), "muted", muted);
    mutedField.classList.add("full");

    const actions = el("div", "form-actions");
    const save = button(tr("device.sound.apply"), { iconName: "check", type: "submit" });
    actions.append(save);
    form.append(volumeField, mutedField, actions);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const nextVolume = Number(data.get("volume_percent"));
      const nextMuted = data.get("muted") === "on";
      const patch = {};
      if (nextVolume !== volume) patch.volumePercent = nextVolume;
      if (nextMuted !== muted) patch.muted = nextMuted;

      save.disabled = true;
      try {
        if (!Object.keys(patch).length) {
          await this.state.refreshSystemControls();
          this.showFlash(tr("device.sound.up_to_date"));
          return;
        }
        await this.api.updateSystemControls(patch);
        await this.state.refreshSystemControls();
        this.showFlash(tr("device.sound.applied"));
      } catch (error) {
        this.showFlash(error?.message || tr("device.sound.failed"), "error");
      } finally {
        save.disabled = false;
      }
    });

    card.append(form);
    return card;
  };
}

import { el, button } from "./ui.js";

export function installSystemControlViews(proto) {
  proto._systemControlsCard = function(snapshot) {
    const card = el("section", "card span-5");
    card.append(this._cardHeader("Sound output", "Speaker volume and mute"));

    if (snapshot.featureErrors?.systemControls) {
      card.append(
        this._empty(
          "device",
          "Sound controls are unavailable",
          snapshot.featureErrors.systemControls.message || "Try refreshing Greia.",
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
        muted ? "Speakers muted" : `Speakers at ${volume}%`,
        "Greia hardware keys can change the same setting at any time.",
      ),
    );

    const form = el("form", "form-grid");
    const volumeField = this._boundedRangeField("Speaker volume", "volume_percent", volume, {
      min: 0,
      max: 100,
      step: 5,
      format: (number) => `${Math.round(number)}%`,
    });
    volumeField.classList.add("full");
    const mutedField = this._checkField("Mute speakers", "muted", muted);
    mutedField.classList.add("full");

    const actions = el("div", "form-actions");
    const save = button("Apply sound", { iconName: "check", type: "submit" });
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
          this.showFlash("Speaker settings are already up to date.");
          return;
        }
        await this.api.updateSystemControls(patch);
        await this.state.refreshSystemControls();
        this.showFlash("Speaker settings applied.");
      } catch (error) {
        this.showFlash(error?.message || "Could not apply speaker settings.", "error");
      } finally {
        save.disabled = false;
      }
    });

    card.append(form);
    return card;
  };
}

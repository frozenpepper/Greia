const optionalResult = async (promise) => {
  try { return { value: await promise, error: null }; }
  catch (error) { return { value: null, error }; }
};

export class ParentAppState {
  constructor(api) {
    this.api = api;
    this.listeners = new Set();
    this.snapshot = Object.freeze({
      phase: "booting",
      meta: null,
      index: null,
      system: null,
      profiles: [],
      activities: [],
      hardware: null,
      systemControls: null,
      audio: null,
      language: null,
      wifi: null,
      ssh: null,
      systemUpdate: null,
      devices: [],
      parentPassword: null,
      progress: null,
      activityPolicy: null,
      usageLimits: null,
      profileUsageLimit: null,
      selectedProfileId: null,
      featureErrors: {},
      error: null,
    });
  }

  subscribe(listener) {
    this.listeners.add(listener);
    listener(this.snapshot);
    return () => this.listeners.delete(listener);
  }

  publish(patch) {
    this.snapshot = Object.freeze({ ...this.snapshot, ...patch });
    for (const listener of this.listeners) listener(this.snapshot);
  }

  async initialize() {
    let meta = null;
    try { meta = await this.api.meta(); } catch (_) {}
    this.publish({ meta });
    return this.refresh();
  }

  capability(name) {
    return Boolean(this.snapshot.index?.capabilities?.[name]);
  }

  async refresh() {
    this.publish({ phase: "loading", error: null });
    try {
      const index = await this.api.index();
      const [system, profiles, activities, hardware, devices] = await Promise.all([
        this.api.system(),
        this.api.profiles(),
        this.api.activities(),
        this.api.hardware(),
        this.api.devices(),
      ]);
      const selectedProfileId = this.#selectProfileId(profiles);
      const supportsUsageLimits = Boolean(index?.capabilities?.["usage_limits.manage"]);
      const optionalCalls = {
        progress: selectedProfileId ? this.api.progress(selectedProfileId) : Promise.resolve(null),
        activityPolicy: selectedProfileId && index?.capabilities?.["activities.policy"]
          ? this.api.activityPolicy(selectedProfileId)
          : Promise.resolve(null),
        usageLimits: supportsUsageLimits ? this.api.usageLimits() : Promise.resolve(null),
        profileUsageLimit: selectedProfileId && supportsUsageLimits
          ? this.api.profileUsageLimit(selectedProfileId)
          : Promise.resolve(null),
        systemControls: index?.capabilities?.["settings.system_controls"]
          ? this.api.systemControls()
          : Promise.resolve(null),
        audio: index?.capabilities?.["settings.audio"] ? this.api.audio() : Promise.resolve(null),
        language: index?.capabilities?.["settings.language"] ? this.api.language() : Promise.resolve(null),
        wifi: index?.capabilities?.["network.manage"] ? this.api.wifi() : Promise.resolve(null),
        ssh: index?.capabilities?.["maintenance.ssh"] ? this.api.ssh() : Promise.resolve(null),
        systemUpdate: index?.capabilities?.["system.update.read"] ? this.api.systemUpdate() : Promise.resolve(null),
        parentPassword: index?.capabilities?.["parent.password"] ? this.api.parentPassword() : Promise.resolve(null),
      };
      const entries = await Promise.all(Object.entries(optionalCalls).map(async ([name, call]) => [name, await optionalResult(call)]));
      const optional = Object.fromEntries(entries);
      const featureErrors = {};
      for (const [name, result] of Object.entries(optional)) {
        if (result.error) featureErrors[name] = result.error;
      }
      this.publish({
        phase: "ready",
        index,
        system,
        profiles,
        activities,
        hardware,
        devices,
        selectedProfileId,
        progress: optional.progress.value,
        activityPolicy: optional.activityPolicy.value,
        usageLimits: optional.usageLimits.value,
        profileUsageLimit: optional.profileUsageLimit.value,
        systemControls: optional.systemControls.value,
        audio: optional.audio.value,
        language: optional.language.value,
        wifi: optional.wifi.value,
        ssh: optional.ssh.value,
        systemUpdate: optional.systemUpdate.value,
        parentPassword: optional.parentPassword.value,
        featureErrors,
        error: null,
      });
      return this.snapshot;
    } catch (error) {
      this.publish({ phase: error?.authenticationRequired ? "authentication" : "error", error });
      throw error;
    }
  }

  async selectProfile(profileId) {
    const supportsPolicy = Boolean(this.snapshot.index?.capabilities?.["activities.policy"]);
    const supportsUsageLimits = Boolean(this.snapshot.index?.capabilities?.["usage_limits.manage"]);
    const [progressResult, policyResult, usageResult] = await Promise.all([
      optionalResult(profileId ? this.api.progress(profileId) : Promise.resolve(null)),
      optionalResult(profileId && supportsPolicy ? this.api.activityPolicy(profileId) : Promise.resolve(null)),
      optionalResult(profileId && supportsUsageLimits ? this.api.profileUsageLimit(profileId) : Promise.resolve(null)),
    ]);
    const featureErrors = { ...this.snapshot.featureErrors };
    if (progressResult.error) featureErrors.progress = progressResult.error; else delete featureErrors.progress;
    if (policyResult.error) featureErrors.activityPolicy = policyResult.error; else delete featureErrors.activityPolicy;
    if (usageResult.error) featureErrors.profileUsageLimit = usageResult.error; else delete featureErrors.profileUsageLimit;
    this.publish({
      selectedProfileId: profileId,
      progress: progressResult.value,
      activityPolicy: policyResult.value,
      profileUsageLimit: usageResult.value,
      featureErrors,
    });
  }

  async refreshUsageLimits() {
    if (!this.capability("usage_limits.manage")) return null;
    const profileId = this.snapshot.selectedProfileId;
    const [deviceResult, profileResult] = await Promise.all([
      optionalResult(this.api.usageLimits()),
      optionalResult(profileId ? this.api.profileUsageLimit(profileId) : Promise.resolve(null)),
    ]);
    const featureErrors = { ...this.snapshot.featureErrors };
    if (deviceResult.error) featureErrors.usageLimits = deviceResult.error; else delete featureErrors.usageLimits;
    if (profileResult.error) featureErrors.profileUsageLimit = profileResult.error; else delete featureErrors.profileUsageLimit;
    this.publish({
      usageLimits: deviceResult.value,
      profileUsageLimit: profileResult.value,
      featureErrors,
    });
    if (deviceResult.error) throw deviceResult.error;
    if (profileResult.error) throw profileResult.error;
    return { device: deviceResult.value, profile: profileResult.value };
  }

  async refreshSystemControls() {
    if (!this.capability("settings.system_controls")) return null;
    const result = await optionalResult(this.api.systemControls());
    const featureErrors = { ...this.snapshot.featureErrors };
    if (result.error) featureErrors.systemControls = result.error; else delete featureErrors.systemControls;
    this.publish({ systemControls: result.value, featureErrors });
    if (result.error) throw result.error;
    return result.value;
  }

  async refreshWifi() {
    if (!this.capability("network.manage")) return null;
    const result = await optionalResult(this.api.wifi());
    const featureErrors = { ...this.snapshot.featureErrors };
    if (result.error) featureErrors.wifi = result.error; else delete featureErrors.wifi;
    this.publish({ wifi: result.value, featureErrors });
    if (result.error) throw result.error;
    return result.value;
  }

  async refreshAudio() {
    if (!this.capability("settings.audio")) return null;
    const result = await optionalResult(this.api.audio());
    const featureErrors = { ...this.snapshot.featureErrors };
    if (result.error) featureErrors.audio = result.error; else delete featureErrors.audio;
    this.publish({ audio: result.value, featureErrors });
    if (result.error) throw result.error;
    return result.value;
  }

  async refreshLanguage() {
    if (!this.capability("settings.language")) return null;
    const result = await optionalResult(this.api.language());
    const featureErrors = { ...this.snapshot.featureErrors };
    if (result.error) featureErrors.language = result.error; else delete featureErrors.language;
    this.publish({ language: result.value, featureErrors });
    if (result.error) throw result.error;
    return result.value;
  }

  async refreshSsh() {
    if (!this.capability("maintenance.ssh")) return null;
    const result = await optionalResult(this.api.ssh());
    const featureErrors = { ...this.snapshot.featureErrors };
    if (result.error) featureErrors.ssh = result.error; else delete featureErrors.ssh;
    this.publish({ ssh: result.value, featureErrors });
    if (result.error) throw result.error;
    return result.value;
  }

  #selectProfileId(profiles) {
    const existing = this.snapshot.selectedProfileId;
    if (existing && profiles.some((profile) => profile.profile_id === existing)) return existing;
    return profiles[0]?.profile_id ?? null;
  }
}
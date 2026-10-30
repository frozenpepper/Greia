const optionalResult = async (promise) => {
  try { return { value: await promise, error: null }; }
  catch (error) { return { value: null, error }; }
};

const UPDATE_CAPABILITIES = [
  ["system.update.check", "check_available"],
  ["system.update.prepare", "prepare_available"],
  ["system.update.restart", "restart_available"],
];

function updateCapabilityMismatch(index, systemUpdate) {
  if (!systemUpdate) return false;
  return UPDATE_CAPABILITIES.some(([capability, field]) =>
    typeof systemUpdate[field] === "boolean"
      && Boolean(index?.capabilities?.[capability]) !== systemUpdate[field]
  );
}

export class ParentAppState {
  constructor(api) {
    this.api = api;
    this.listeners = new Set();
    this.systemUpdatePollTimer = null;
    this.systemUpdatePollInFlight = false;
    this.softwareUpdateReconcilePending = false;
    this.softwareUpdateReconcileAttempts = 0;
    this.softwareUpdateReconcileTarget = null;
    this.disposed = false;
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
    this.#syncSystemUpdatePolling();
  }

  dispose() {
    this.disposed = true;
    if (this.systemUpdatePollTimer !== null) clearTimeout(this.systemUpdatePollTimer);
    this.systemUpdatePollTimer = null;
    this.listeners.clear();
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
      let index = await this.api.index();
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
      if (!optional.systemUpdate.error && updateCapabilityMismatch(index, optional.systemUpdate.value)) {
        const refreshedIndex = await optionalResult(this.api.index());
        if (!refreshedIndex.error) index = refreshedIndex.value;
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
        systemUpdate: optional.systemUpdate.error ? this.snapshot.systemUpdate : optional.systemUpdate.value,
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

  async refreshSystemUpdate({ refreshIndex = false } = {}) {
    if (!this.capability("system.update.read")) return null;
    const result = await optionalResult(this.api.systemUpdate());
    const featureErrors = { ...this.snapshot.featureErrors };
    if (result.error) featureErrors.systemUpdate = result.error; else delete featureErrors.systemUpdate;
    let index = this.snapshot.index;
    const statusChanged = !result.error && updateCapabilityMismatch(index, result.value);
    if (!result.error && (refreshIndex || statusChanged)) {
      const refreshedIndex = await optionalResult(this.api.index());
      if (refreshedIndex.error) featureErrors.systemUpdateIndex = refreshedIndex.error;
      else {
        index = refreshedIndex.value;
        delete featureErrors.systemUpdateIndex;
      }
    }
    if (this.softwareUpdateReconcilePending) {
      this.softwareUpdateReconcileAttempts += 1;
      if (
        !result.error
        && this.#softwareUpdateOperationAccepted(
          result.value?.software_update,
          this.softwareUpdateReconcileTarget,
        )
      ) {
        this.softwareUpdateReconcilePending = false;
        this.softwareUpdateReconcileAttempts = 0;
        this.softwareUpdateReconcileTarget = null;
      } else if (this.softwareUpdateReconcileAttempts >= 12) {
        this.softwareUpdateReconcilePending = false;
        this.softwareUpdateReconcileTarget = null;
      }
    }
    this.publish({
      systemUpdate: result.error ? this.snapshot.systemUpdate : result.value,
      index,
      featureErrors,
    });
    if (result.error) throw result.error;
    return result.value;
  }

  async checkSystemUpdate() {
    if (!this.capability("system.update.check") || this.snapshot.systemUpdate?.check_available !== true) {
      throw new Error("Online Greia update checks are unavailable");
    }
    return this.#startSystemUpdateOperation(() => this.api.checkSystemUpdate());
  }

  async prepareSystemUpdate(releaseId) {
    const releases = this.snapshot.systemUpdate?.delivery?.catalog?.releases;
    const listed = Array.isArray(releases) && releases.some((release) => release?.release_id === releaseId);
    if (!this.capability("system.update.prepare") || this.snapshot.systemUpdate?.prepare_available !== true || !listed) {
      throw new Error("This Greia cannot prepare that update");
    }
    return this.#startSystemUpdateOperation(() => this.api.prepareSystemUpdate(releaseId));
  }

  async restartSystemUpdate() {
    if (!this.capability("system.update.restart") || this.snapshot.systemUpdate?.restart_available !== true) {
      throw new Error("This Greia cannot restart into the prepared update");
    }
    return this.#startSystemUpdateOperation(() => this.api.restartSystemUpdate());
  }

  async uploadSoftwareUpdatePackage(file) {
    const status = this.snapshot.systemUpdate?.software_update;
    if (!this.capability("system.update.package.install") || status?.available !== true || status.job && !["applied", "rolled_back", "failed"].includes(status.job.state)) {
      throw new Error(status?.reason || "This Greia cannot install a software update package");
    }
    return this.#startSoftwareUpdateOperation(() => this.api.uploadSoftwareUpdatePackage(file));
  }

  async restartSoftwareUpdatePackage() {
    const status = this.snapshot.systemUpdate?.software_update;
    if (!this.capability("system.update.package.install") || status?.available !== true || status?.restart_available !== true || status?.job?.state !== "ready_to_restart") {
      throw new Error("This Greia cannot restart into the prepared software update");
    }
    return this.#startSoftwareUpdateOperation(() => this.api.restartSoftwareUpdatePackage(), { restart: true });
  }

  async #startSystemUpdateOperation(start) {
    let operationError = null;
    try {
      await start();
    } catch (error) {
      operationError = error;
    }
    // The device persists accepted jobs. Always reconcile after the POST so a
    // lost response or phone disconnect cannot make the UI assume it stopped.
    try {
      await this.refreshSystemUpdate({ refreshIndex: true });
    } catch (refreshError) {
      if (!operationError) operationError = refreshError;
    }
    if (operationError) throw operationError;
    return this.snapshot.systemUpdate;
  }

  async #startSoftwareUpdateOperation(start, { restart = false } = {}) {
    const previous = this.snapshot.systemUpdate?.software_update || {};
    let accepted = null;
    let operationError = null;
    try {
      accepted = await start();
    } catch (error) {
      operationError = error;
    }
    if (!operationError && !this.#hasSoftwareUpdateReceipt(accepted)) {
      operationError = Object.assign(
        new Error("Greia did not return a valid software update job receipt"),
        { code: "invalid_update_receipt", status: 0 },
      );
    }
    const reconciliationTarget = {
      restart,
      previousJobId: previous.job?.job_id ?? null,
      previousRestartAvailable: previous.restart_available === true,
    };
    const acceptedJob = !operationError && accepted?.job;
    if (this.#isSoftwareUpdateJob(acceptedJob)) {
      const current = this.snapshot.systemUpdate || {};
      const softwareUpdate = current.software_update || {};
      this.publish({
        systemUpdate: {
          ...current,
          software_update: {
            ...softwareUpdate,
            job: acceptedJob,
            restart_available: acceptedJob.restart_available === true,
          },
        },
      });
    }
    // A lost POST reply is ambiguous: the device may already have durably
    // accepted the request. Reconcile its status before showing a failure.
    // If that GET is also lost, retry a bounded number of times in the
    // background while retaining the prior status.
    if (operationError) {
      const statusCode = operationError?.status;
      const ambiguousReply = operationError?.code === "invalid_update_receipt"
        || operationError?.code === "network_error"
        || operationError?.name === "AbortError"
        || statusCode === 0
        || (Number.isInteger(statusCode) && statusCode >= 500);
      if (ambiguousReply) {
        this.softwareUpdateReconcilePending = true;
        this.softwareUpdateReconcileAttempts = 0;
        this.softwareUpdateReconcileTarget = reconciliationTarget;
      }
      try {
        await this.refreshSystemUpdate({ refreshIndex: true });
      } catch (_) {
        // The bounded reconciliation poll remains armed after an ambiguous
        // POST and a failed status read.
      }
      const current = this.snapshot.systemUpdate?.software_update || {};
      if (ambiguousReply && this.#softwareUpdateOperationAccepted(current, reconciliationTarget)) {
        this.softwareUpdateReconcilePending = false;
        this.softwareUpdateReconcileAttempts = 0;
        this.softwareUpdateReconcileTarget = null;
        this.#syncSystemUpdatePolling();
        return { job: current.job };
      }
      if (ambiguousReply) this.#syncSystemUpdatePolling();
      throw operationError;
    }
    // A reboot or network loss can make the immediate GET fail after the
    // 202 acknowledgement; the accepted receipt above remains in the snapshot
    // and active-job polling will reconnect later.
    await this.refreshSystemUpdate({ refreshIndex: true }).catch(() => undefined);
    return accepted;
  }

  #softwareUpdateOperationAccepted(status, target) {
    if (!target || !status || typeof status !== "object") return false;
    const job = status.job;
    if (!this.#isSoftwareUpdateJob(job)) return false;
    if (target.restart) {
      return target.previousRestartAvailable === true
        && job.job_id === target.previousJobId
        && (job.state !== "ready_to_restart" || status.restart_available !== true);
    }
    return job.job_id !== target.previousJobId;
  }

  #hasSoftwareUpdateReceipt(receipt) {
    const job = receipt?.job;
    return this.#isSoftwareUpdateJob(job);
  }

  #isSoftwareUpdateJob(job) {
    return Boolean(
      job
      && typeof job === "object"
      && !Array.isArray(job)
      && typeof job.job_id === "string"
      && /^[0-9a-f]{32}$/.test(job.job_id)
      && ["queued", "validating", "waiting_for_idle", "applying", "restarting", "ready_to_restart", "applied", "rolled_back", "failed"].includes(job.state),
    );
  }

  #syncSystemUpdatePolling() {
    if (this.disposed) return;
    const job = this.snapshot.systemUpdate?.delivery?.job;
    const softwareJob = this.snapshot.systemUpdate?.software_update?.job;
    const softwareRestartPending = softwareJob?.state === "ready_to_restart"
      && this.snapshot.systemUpdate?.software_update?.restart_available !== true;
    const active = ["checking", "queued", "downloading", "receiving", "verifying", "staging", "restart_pending"].includes(job?.state)
      || ["queued", "validating", "waiting_for_idle", "applying", "restarting"].includes(softwareJob?.state)
      || softwareRestartPending
      || (this.softwareUpdateReconcilePending && this.softwareUpdateReconcileAttempts < 12);
    if (!active) {
      if (this.systemUpdatePollTimer !== null) clearTimeout(this.systemUpdatePollTimer);
      this.systemUpdatePollTimer = null;
      return;
    }
    if (this.systemUpdatePollTimer !== null || this.systemUpdatePollInFlight) return;
    this.systemUpdatePollTimer = setTimeout(() => {
      this.systemUpdatePollTimer = null;
      if (this.systemUpdatePollInFlight) return;
      this.systemUpdatePollInFlight = true;
      void this.refreshSystemUpdate().catch(() => undefined).finally(() => {
        this.systemUpdatePollInFlight = false;
        this.#syncSystemUpdatePolling();
      });
    }, 2500);
  }

  #selectProfileId(profiles) {
    const existing = this.snapshot.selectedProfileId;
    if (existing && profiles.some((profile) => profile.profile_id === existing)) return existing;
    return profiles[0]?.profile_id ?? null;
  }
}

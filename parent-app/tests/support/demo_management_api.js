import { DemoParentApiClient } from "./demo_api.js";

const demoAddedActivity = () => ({
  activity_id: "org.greia.labirinti",
  version: "0.3.0",
  title_key: "Labirinti",
  icon_id: "maze",
  categories: ["logic", "spatial"],
  launcher_categories: ["play", "learn"],
  presentation_categories: ["play", "learn"],
  discovery_tags: ["mazes", "puzzles"],
  difficulty: 3,
  difficulty_min: 1,
  difficulty_max: 6,
  adaptive_difficulty: true,
  recommended_age_min: 3,
  recommended_age_max: 8,
  languages: ["it", "en"],
  input_profile: "directional",
  package_trust: "parent_trusted_unsigned",
  source_id: "greia-parent-package-service",
  removable: true,
});

const validateDailyMinutes = (value) => {
  if (value === null) return null;
  if (!Number.isInteger(value) || value < 1 || value > 1440) throw new Error("Daily Activity time must be between 1 and 1440 minutes, or unlimited.");
  return value;
};

const validateDifficulty = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  if (!Number.isInteger(number) || number < 1 || number > 10) throw new Error("Difficulty must be between 1 and 10.");
  return number;
};

const validateVolumePercent = (value) => {
  if (!Number.isInteger(value) || value < 0 || value > 100) throw new Error("Speaker volume must be between 0 and 100 percent.");
  return value;
};

const canonicalVisibilityMode = (value) => value === "hide_too_simple" ? "age_and_easier" : value;
const validateVisibilityMode = (value) => {
  const mode = canonicalVisibilityMode(value || "show_all");
  if (!["show_all", "recommended_only", "age_and_easier", "custom"].includes(mode)) throw new Error("Invalid Activity visibility mode.");
  return mode;
};

const remainingSeconds = (dailyMinutes, usedSeconds) => dailyMinutes === null ? null : Math.max(0, dailyMinutes * 60 - usedSeconds);
const mostRestrictive = (...values) => {
  const finite = values.filter((value) => value !== null && value !== undefined);
  return finite.length ? Math.min(...finite) : null;
};

const difficultyMatches = (activity, minimum, maximum) => {
  if (minimum === null && maximum === null) return true;
  const fixed = Number(activity?.difficulty ?? 1);
  const low = activity?.adaptive_difficulty ? Number(activity?.difficulty_min ?? fixed) : fixed;
  const high = activity?.adaptive_difficulty ? Number(activity?.difficulty_max ?? fixed) : fixed;
  return (minimum === null || high >= minimum) && (maximum === null || low <= maximum);
};

const ageMatches = (activity, profile, rawMode) => {
  const age = profile?.approximate_age;
  const mode = canonicalVisibilityMode(rawMode);
  if (age === null || age === undefined || ["show_all", "custom"].includes(mode)) return true;
  const minimum = activity?.recommended_age_min;
  const maximum = activity?.recommended_age_max;
  const hasAudience = minimum !== null && minimum !== undefined || maximum !== null && maximum !== undefined;
  if (!hasAudience) return false;
  if (mode === "age_and_easier") return minimum === null || minimum === undefined || minimum <= age;
  if (mode === "recommended_only") return (minimum === null || minimum === undefined || age >= minimum) && (maximum === null || maximum === undefined || age <= maximum);
  return true;
};

export class DemoManagementApiClient extends DemoParentApiClient {
  constructor() {
    super();
    this.presentationByProfile = new Map([
      ["greta", "girl"],
      ["gaia", "girl"],
    ]);
    this.addedActivities = [demoAddedActivity()];
    this.deviceUsage = { daily_minutes: 120, used_seconds: 47 * 60 };
    this.profileUsage = new Map([
      ["greta", { daily_minutes: 90, used_seconds: 35 * 60 }],
      ["gaia", { daily_minutes: null, used_seconds: 12 * 60 }],
    ]);
    this.systemControlsData = {
      schema_version: 1,
      volume_percent: 70,
      muted: false,
      brightness_percent: 100,
    };
    for (const [profileId, policy] of this.policies.entries()) {
      this.policies.set(profileId, {
        difficulty_min: null,
        difficulty_max: null,
        ...policy,
        visibility_mode: validateVisibilityMode(policy.visibility_mode),
      });
    }
  }

  async index() {
    const payload = await super.index();
    return {
      ...payload,
      capabilities: {
        ...payload.capabilities,
        "profiles.presentation": true,
        "usage_limits.manage": true,
        "activities.install": true,
        "activities.remove": true,
        "settings.system_controls": true,
      },
    };
  }

  async profiles() {
    const profiles = await super.profiles();
    return profiles.map((profile) => {
      const presentation = this.presentationByProfile.get(profile.profile_id) || "neutral";
      return {
        ...profile,
        presentation,
        grammatical_gender: presentation === "boy" ? "masculine" : presentation === "girl" ? "feminine" : "neutral",
      };
    });
  }

  async profilePresentation(profileId) {
    const presentation = this.presentationByProfile.get(profileId) || "neutral";
    return {
      profile_id: profileId,
      presentation,
      grammatical_gender: presentation === "boy" ? "masculine" : presentation === "girl" ? "feminine" : "neutral",
    };
  }

  async updateProfilePresentation(profileId, { presentation }) {
    if (!["neutral", "boy", "girl"].includes(presentation)) throw new Error("Invalid presentation.");
    this.presentationByProfile.set(profileId, presentation);
    return this.profilePresentation(profileId);
  }

  async createProfile(profile) {
    const created = await super.createProfile(profile);
    this.presentationByProfile.set(created.profile_id, "neutral");
    this.profileUsage.set(created.profile_id, { daily_minutes: null, used_seconds: 0 });
    const policy = this.policies.get(created.profile_id) || { profile_id: created.profile_id, visibility_mode: "show_all", overrides: {} };
    this.policies.set(created.profile_id, { difficulty_min: null, difficulty_max: null, ...policy });
    return created;
  }

  async deleteProfile(profileId) {
    this.presentationByProfile.delete(profileId);
    this.profileUsage.delete(profileId);
    return super.deleteProfile(profileId);
  }

  async usageLimits() {
    const remaining = remainingSeconds(this.deviceUsage.daily_minutes, this.deviceUsage.used_seconds);
    return {
      date: "2026-09-01",
      daily_minutes: this.deviceUsage.daily_minutes,
      used_seconds: this.deviceUsage.used_seconds,
      remaining_seconds: remaining,
      exhausted: remaining === 0,
      counting_mode: "activity_time",
    };
  }

  async updateUsageLimits(dailyMinutes) {
    this.deviceUsage.daily_minutes = validateDailyMinutes(dailyMinutes);
    return this.usageLimits();
  }

  async profileUsageLimit(profileId) {
    const profile = this.profilesData.find((item) => item.profile_id === profileId);
    if (!profile) throw new Error("Profile does not exist.");
    const own = this.profileUsage.get(profileId) || { daily_minutes: null, used_seconds: 0 };
    const deviceRemaining = remainingSeconds(this.deviceUsage.daily_minutes, this.deviceUsage.used_seconds);
    const profileRemaining = remainingSeconds(own.daily_minutes, own.used_seconds);
    const effectiveRemaining = mostRestrictive(deviceRemaining, profileRemaining);
    return {
      date: "2026-09-01",
      profile_id: profileId,
      device_daily_minutes: this.deviceUsage.daily_minutes,
      profile_daily_minutes: own.daily_minutes,
      device_used_seconds: this.deviceUsage.used_seconds,
      profile_used_seconds: own.used_seconds,
      device_remaining_seconds: deviceRemaining,
      profile_remaining_seconds: profileRemaining,
      effective_remaining_seconds: effectiveRemaining,
      exhausted: effectiveRemaining === 0,
      counting_mode: "activity_time",
    };
  }

  async updateProfileUsageLimit(profileId, dailyMinutes) {
    const current = this.profileUsage.get(profileId) || { daily_minutes: null, used_seconds: 0 };
    this.profileUsage.set(profileId, { ...current, daily_minutes: validateDailyMinutes(dailyMinutes) });
    return this.profileUsageLimit(profileId);
  }

  async systemControls() {
    return structuredClone(this.systemControlsData);
  }

  async updateSystemControls(settings) {
    if (!settings || typeof settings !== "object" || Array.isArray(settings)) throw new Error("System controls object is required.");
    const allowed = new Set(["volumePercent", "muted"]);
    const unknown = Object.keys(settings).filter((key) => !allowed.has(key));
    if (unknown.length) throw new Error(`Unsupported system control field: ${unknown.sort().join(", ")}`);
    if (Object.hasOwn(settings, "volumePercent")) {
      this.systemControlsData.volume_percent = validateVolumePercent(settings.volumePercent);
    }
    if (Object.hasOwn(settings, "muted")) {
      if (typeof settings.muted !== "boolean") throw new Error("Mute setting must be boolean.");
      this.systemControlsData.muted = settings.muted;
    }
    if (!Object.hasOwn(settings, "volumePercent") && !Object.hasOwn(settings, "muted")) {
      throw new Error("At least one system control is required.");
    }
    return this.systemControls();
  }

  async activities() {
    const builtIns = (await super.activities()).map((activity) => ({
      ...activity,
      launcher_categories: activity.launcher_categories || activity.presentation_categories || [],
      package_trust: "built_in",
      source_id: "greia-system",
      removable: false,
    }));
    return [...builtIns, ...structuredClone(this.addedActivities)];
  }

  async activityPolicy(profileId) {
    await super.activityPolicy(profileId);
    const profile = this.profilesData.find((item) => item.profile_id === profileId);
    if (!profile) throw new Error("Profile does not exist.");
    const policy = this.policies.get(profileId) || {
      profile_id: profileId,
      visibility_mode: "show_all",
      difficulty_min: null,
      difficulty_max: null,
      overrides: {},
    };
    const mode = validateVisibilityMode(policy.visibility_mode);
    const all = await this.activities();
    const effective = [];
    for (const activity of all) {
      const override = policy.overrides?.[activity.activity_id];
      if (override === "always_hide") continue;
      if (override === "always_show" || (
        ageMatches(activity, profile, mode)
        && difficultyMatches(activity, policy.difficulty_min ?? null, policy.difficulty_max ?? null)
      )) effective.push(activity.activity_id);
    }

    return {
      profile_id: profileId,
      visibility_mode: mode,
      difficulty_min: policy.difficulty_min ?? null,
      difficulty_max: policy.difficulty_max ?? null,
      overrides: structuredClone(policy.overrides || {}),
      effective_activity_ids: effective,
    };
  }

  async updateActivityPolicy(profileId, patch) {
    const current = this.policies.get(profileId) || {
      profile_id: profileId,
      visibility_mode: "show_all",
      difficulty_min: null,
      difficulty_max: null,
      overrides: {},
    };
    const minimum = validateDifficulty(Object.hasOwn(patch, "difficulty_min") ? patch.difficulty_min : current.difficulty_min);
    const maximum = validateDifficulty(Object.hasOwn(patch, "difficulty_max") ? patch.difficulty_max : current.difficulty_max);
    if (minimum !== null && maximum !== null && minimum > maximum) throw new Error("Minimum difficulty cannot be greater than maximum difficulty.");
    const overrides = Object.fromEntries(
      Object.entries(patch.overrides || current.overrides || {})
        .filter(([, value]) => value && value !== "default"),
    );
    this.policies.set(profileId, {
      profile_id: profileId,
      visibility_mode: validateVisibilityMode(patch.visibility_mode || current.visibility_mode),
      difficulty_min: minimum,
      difficulty_max: maximum,
      overrides,
    });
    return this.activityPolicy(profileId);
  }

  async installActivity(file) {
    const name = file?.name?.replace(/\.greiaactivity$/i, "") || `demo-${Date.now()}`;
    const activityId = name.includes(".") ? name : `org.greia.${name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "demo"}`;
    if (this.addedActivities.some((activity) => activity.activity_id === activityId)) throw new Error("That Activity is already installed.");
    this.addedActivities.push({
      ...demoAddedActivity(),
      activity_id: activityId,
      title_key: name.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()),
      version: "0.1.0",
    });
    return { installed: { activity_id: activityId, profile_data_preserved: true } };
  }

  async removeActivity(activityId) {
    const index = this.addedActivities.findIndex((activity) => activity.activity_id === activityId);
    if (index < 0) throw new Error("Built-in Activities cannot be removed.");
    const [removed] = this.addedActivities.splice(index, 1);
    for (const policy of this.policies.values()) {
      if (policy.overrides) delete policy.overrides[activityId];
    }
    return {
      removed: {
        activity_id: removed.activity_id,
        version: removed.version,
        source_id: "greia-parent-package-service",
        profile_data_preserved: true,
      },
    };
  }
}
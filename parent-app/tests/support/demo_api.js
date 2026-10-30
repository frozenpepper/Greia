const wait = (ms = 30) => new Promise((resolve) => setTimeout(resolve, ms));

const ACTIVITIES = [
  {
    activity_id: "org.greia.painting",
    version: "0.1.0",
    title_key: "Painting",
    icon_id: "paint",
    categories: ["creativity", "art"],
    presentation_categories: ["create"],
    discovery_tags: ["drawing", "making"],
    difficulty: 1,
    recommended_age_min: 3,
    recommended_age_max: null,
    difficulty_min: null,
    difficulty_max: null,
    adaptive_difficulty: false,
    languages: ["en", "it"],
    input_profile: "pointer",
  },
  {
    activity_id: "org.greia.writing",
    version: "0.1.0",
    title_key: "Writing",
    icon_id: "writing",
    categories: ["creativity", "writing"],
    presentation_categories: ["create", "learn"],
    discovery_tags: ["writing", "stories"],
    difficulty: 3,
    recommended_age_min: 5,
    recommended_age_max: null,
    difficulty_min: null,
    difficulty_max: null,
    adaptive_difficulty: false,
    languages: ["en", "it"],
    input_profile: "text",
  },
  {
    activity_id: "org.greia.treno-numeri",
    version: "0.1.0",
    title_key: "Il Treno dei Numeri",
    icon_id: "robot",
    categories: ["early_math", "counting"],
    presentation_categories: ["learn", "play"],
    discovery_tags: ["numbers", "puzzles"],
    difficulty: 2,
    recommended_age_min: 4,
    recommended_age_max: 7,
    difficulty_min: null,
    difficulty_max: null,
    adaptive_difficulty: false,
    languages: ["it", "en"],
    input_profile: "hybrid",
  },
  {
    activity_id: "org.greia.teatrino-fiabe",
    version: "0.2.0",
    title_key: "Teatrino delle Fiabe",
    icon_id: "stories",
    categories: ["creativity", "storytelling"],
    presentation_categories: ["create", "play"],
    discovery_tags: ["stories", "making"],
    difficulty: 2,
    recommended_age_min: 3,
    recommended_age_max: 9,
    difficulty_min: 1,
    difficulty_max: 5,
    adaptive_difficulty: true,
    languages: ["it", "en"],
    input_profile: "hybrid",
  },
  {
    activity_id: "org.greia.clinic",
    version: "0.1.0",
    title_key: "Clinica degli Animali",
    icon_id: "care",
    categories: ["empathy", "caregiving"],
    presentation_categories: ["play", "learn"],
    discovery_tags: ["care"],
    difficulty: 3,
    recommended_age_min: 4,
    recommended_age_max: 8,
    difficulty_min: null,
    difficulty_max: null,
    adaptive_difficulty: false,
    languages: ["it", "en"],
    input_profile: "hybrid",
  },
];

const DEFAULT_HARDWARE = Object.freeze({
  mouse_speed: 0,
  touchpad_speed: 0.5,
  touchpad_tap: true,
  natural_scrolling: false,
  resolution: "auto",
  keyboard_layout: "us",
  mic_gain: 2.0,
});

const DEFAULT_AUDIO = Object.freeze({
  schema_version: 1,
  microphone_processing_enabled: true,
  advanced_noise_reduction: false,
});

export class DemoParentApiClient {
  constructor() {
    this.origin = "demo://greia-bedroom";
    this.profilesData = [
      {
        profile_id: "greta",
        display_name: "Greta",
        avatar_id: "unicorn",
        has_secret: false,
        mask_secret: false,
        approximate_age: 6,
        challenge_preference: "standard",
      },
      {
        profile_id: "gaia",
        display_name: "Gaia",
        avatar_id: "owl",
        has_secret: true,
        mask_secret: false,
        approximate_age: 4,
        challenge_preference: "automatic",
      },
    ];
    this.policies = new Map([
      ["greta", { profile_id: "greta", visibility_mode: "show_all", overrides: {} }],
      ["gaia", { profile_id: "gaia", visibility_mode: "recommended_only", overrides: {} }],
    ]);
    this.hardwareData = {
      desired: { ...DEFAULT_HARDWARE, mouse_speed: 0.25, natural_scrolling: true },
      applied: true,
      display_output: "eDP-1",
      message: "Settings applied",
      display_modes: [
        { id: "1024x600", width: 1024, height: 600, refresh_hz: 60, preferred: true, current: true },
        { id: "800x600", width: 800, height: 600, refresh_hz: 60, preferred: false, current: false },
      ],
    };
    this.audioData = this.#audioPayload({ ...DEFAULT_AUDIO });
    this.languageData = {
      locale: "it",
      selected: { locale: "it", name: "Italiano", native_name: "Italiano", flag: "🇮🇹" },
      languages: [
        { locale: "it", name: "Italiano", native_name: "Italiano", flag: "🇮🇹" },
        { locale: "en", name: "English", native_name: "English", flag: "🇬🇧" },
        { locale: "fr", name: "French", native_name: "Français", flag: "🇫🇷" },
        { locale: "es", name: "Spanish", native_name: "Español", flag: "🇪🇸" },
      ],
    };
    this.wifiData = {
      available: true,
      networks: [
        { ssid: "Casa", security: "psk", signal_dbm: -41 },
        { ssid: "Studio", security: "psk", signal_dbm: -58 },
        { ssid: "Guest WiFi", security: "open", signal_dbm: -67 },
      ],
    };
    this.sshData = {
      active: false,
      enabled: false,
      port: 22,
      username: "greia",
      host_ip: "192.168.1.64",
      connection_string: "ssh greia@192.168.1.64",
    };
    this.devicesData = [
      { device_id: "phone-1", display_name: "Dad's phone", created_at: "2026-08-22T19:34:00Z" },
      { device_id: "tablet-1", display_name: "Kitchen iPad", created_at: "2026-08-20T18:10:00Z" },
    ];
    this.updateData = {
      state: "idle",
      upload_available: false,
      activation_available: false,
      activation_reason: "A/B system-slot backend is not configured for this image",
    };
  }

  async meta() {
    await wait();
    return {
      product: "Greia",
      service: "Greia Parents",
      device_name: "greia-bedroom",
      api_version: 1,
      transport_security: "provisional-http",
    };
  }

  async index() {
    await wait();
    return {
      api_version: 1,
      capabilities: {
        "profiles.manage": true,
        "activities.read": true,
        "activities.policy": true,
        "progress.read": true,
        "settings.input": true,
        "settings.display": true,
        "settings.language": true,
        "paired_devices.manage": true,
        "activities.install": true,
        "backup.manage": false,
        "settings.audio": true,
        "network.manage": true,
        "maintenance.ssh": true,
        "parent.password": true,
        "system.update.read": true,
        "system.update.upload": false,
        "system.update.activate": false,
      },
    };
  }

  async system() {
    await wait();
    return {
      uptime_seconds: 14582,
      memory_available_bytes: 392 * 1048576,
      memory_total_bytes: 768 * 1048576,
      disk_free_bytes: 4610 * 1048576,
      disk_total_bytes: 7168 * 1048576,
      runtime_api_version: "0.1",
      activities: ACTIVITIES.map((activity) => activity.activity_id),
      profile_policy: { avatars: ["unicorn", "owl", "robot", "rabbit", "star"] },
    };
  }

  async profiles() { await wait(); return structuredClone(this.profilesData); }
  async activities() { await wait(); return structuredClone(ACTIVITIES); }
  async hardware() { await wait(); return structuredClone(this.hardwareData); }
  async audio() { await wait(); return structuredClone(this.audioData); }
  async language() { await wait(); return structuredClone(this.languageData); }
  async wifi() { await wait(); return structuredClone(this.wifiData); }
  async ssh() { await wait(); return structuredClone(this.sshData); }
  async systemUpdate() { await wait(); return structuredClone(this.updateData); }
  async devices() { await wait(); return structuredClone(this.devicesData); }
  async parentPassword() { await wait(); return { configured: true, username: "greia", changeable: true }; }

  async progress(profileId) {
    await wait();
    const ids = profileId === "greta"
      ? ["org.greia.teatrino-fiabe", "org.greia.painting"]
      : ["org.greia.treno-numeri", "org.greia.clinic"];
    return {
      available: true,
      profile_id: profileId,
      reward_balances: { star: profileId === "greta" ? 18 : 11 },
      recent_sessions: ids.map((activity_id) => ({ activity_id, exit_reason: "normal" })),
    };
  }

  async pairBootstrap() {
    await wait();
    return {
      device: { device_id: "demo", display_name: "Demo browser" },
      credential: "demo-credential-long-enough",
    };
  }

  forgetCredential() {}

  async createProfile(profile) {
    await wait();
    const item = {
      profile_id: `demo-${Date.now()}`,
      display_name: profile.display_name,
      avatar_id: profile.avatar_id,
      has_secret: Boolean(profile.secret),
      mask_secret: Boolean(profile.mask_secret),
      approximate_age: profile.approximate_age ?? null,
      challenge_preference: profile.challenge_preference || "automatic",
    };
    this.profilesData.push(item);
    this.policies.set(item.profile_id, {
      profile_id: item.profile_id,
      visibility_mode: "show_all",
      overrides: {},
    });
    return structuredClone(item);
  }

  async updateProfile(profileId, patch) {
    await wait();
    const index = this.profilesData.findIndex((profile) => profile.profile_id === profileId);
    if (index < 0) throw new Error("Profile does not exist.");
    const current = this.profilesData[index];
    const action = patch.secret_action || "keep";
    let hasSecret = current.has_secret;
    if (action === "set") hasSecret = Boolean(patch.secret);
    if (action === "clear") hasSecret = false;
    this.profilesData[index] = {
      ...current,
      display_name: patch.display_name ?? current.display_name,
      avatar_id: patch.avatar_id ?? current.avatar_id,
      has_secret: hasSecret,
      mask_secret: Object.hasOwn(patch, "mask_secret")
        ? Boolean(patch.mask_secret)
        : current.mask_secret,
      approximate_age: Object.hasOwn(patch, "approximate_age")
        ? patch.approximate_age
        : current.approximate_age,
      challenge_preference: patch.challenge_preference || current.challenge_preference,
    };
    return structuredClone(this.profilesData[index]);
  }

  async deleteProfile(profileId) {
    await wait();
    this.profilesData = this.profilesData.filter((profile) => profile.profile_id !== profileId);
    this.policies.delete(profileId);
    return { deleted: profileId };
  }

  async activityPolicy(profileId) {
    await wait();
    const profile = this.profilesData.find((item) => item.profile_id === profileId);
    if (!profile) throw new Error("Profile does not exist.");
    const policy = this.policies.get(profileId) || {
      profile_id: profileId,
      visibility_mode: "show_all",
      overrides: {},
    };
    return {
      ...structuredClone(policy),
      effective_activity_ids: this.#effective(profile, policy),
    };
  }

  async updateActivityPolicy(profileId, patch) {
    await wait();
    const current = await this.activityPolicy(profileId);
    const next = {
      profile_id: profileId,
      visibility_mode: patch.visibility_mode || current.visibility_mode,
      overrides: Object.fromEntries(
        Object.entries(patch.overrides || current.overrides || {})
          .filter(([, value]) => value && value !== "default"),
      ),
    };
    this.policies.set(profileId, next);
    const profile = this.profilesData.find((item) => item.profile_id === profileId);
    return {
      ...structuredClone(next),
      effective_activity_ids: this.#effective(profile, next),
    };
  }

  async changeParentPassword({ currentPassword, newPassword }) {
    await wait();
    if (currentPassword !== "greia") throw new Error("Current Parent password is incorrect.");
    if (!newPassword || newPassword.length < 4) {
      throw new Error("Parent password must be at least 4 characters.");
    }
    return { changed: true };
  }

  async updateLanguage(locale) {
    await wait();
    const selected = this.languageData.languages.find((language) => language.locale === locale);
    if (!selected) throw new Error("That language is not available on this Greia.");
    this.languageData.locale = locale;
    this.languageData.selected = selected;
    return structuredClone(this.languageData);
  }

  async connectWifi({ ssid, passphrase = "" }) {
    await wait();
    const network = this.wifiData.networks.find((item) => item.ssid === ssid);
    if (!network) throw new Error("That Wi-Fi network is no longer available.");
    if (network.security === "psk" && passphrase.length < 8) {
      throw new Error("Wi-Fi password must be at least 8 characters.");
    }
    return { connected: true, ssid };
  }

  async updateSsh({ enabled }) {
    await wait();
    this.sshData.active = Boolean(enabled);
    this.sshData.enabled = Boolean(enabled);
    return structuredClone(this.sshData);
  }

  async updateHardware(settings) {
    await wait();
    if (Object.hasOwn(settings, "mic_gain")) {
      const gain = Number(settings.mic_gain);
      if (!Number.isFinite(gain) || gain < 0.5 || gain > 4.0) {
        throw new Error("Microphone level must be between 50% and 400%.");
      }
    }
    this.hardwareData.desired = { ...this.hardwareData.desired, ...settings };
    this.hardwareData.applied = true;
    return structuredClone(this.hardwareData);
  }

  async resetHardware() {
    await wait();
    this.hardwareData.desired = { ...DEFAULT_HARDWARE };
    return structuredClone(this.hardwareData);
  }

  async updateAudio(settings) {
    await wait();
    const current = this.audioData.desired;
    const next = {
      ...current,
      ...(Object.hasOwn(settings, "microphone_processing_enabled")
        ? { microphone_processing_enabled: Boolean(settings.microphone_processing_enabled) }
        : {}),
      ...(Object.hasOwn(settings, "advanced_noise_reduction")
        ? { advanced_noise_reduction: Boolean(settings.advanced_noise_reduction) }
        : {}),
    };
    this.audioData = this.#audioPayload(next);
    return structuredClone(this.audioData);
  }

  async resetAudio() {
    await wait();
    this.audioData = this.#audioPayload({ ...DEFAULT_AUDIO });
    return structuredClone(this.audioData);
  }

  async revokeDevice(deviceId) {
    await wait();
    const found = this.devicesData.find((device) => device.device_id === deviceId);
    this.devicesData = this.devicesData.filter((device) => device.device_id !== deviceId);
    return { revoked: found ?? null };
  }

  async installActivity(file) {
    await wait();
    return {
      installed: {
        activity_id: file?.name?.replace(/\.greiaactivity$/i, "") || "org.greia.demo",
      },
    };
  }

  async uploadSystemUpdate(file) {
    await wait();
    return { received: { version: file?.name || "demo-update" } };
  }

  #audioPayload(desired) {
    const mode = !desired.microphone_processing_enabled
      ? "off"
      : desired.advanced_noise_reduction
        ? "advanced"
        : "lightweight";
    return {
      desired: { ...desired },
      effective: {
        microphone_processing_mode: mode,
        capture_device: mode === "off" ? "default" : mode === "advanced" ? "greia_mic_advanced" : "greia_mic_light",
        fallback_reason: null,
      },
      available: { lightweight: true, advanced: true },
      backend: "demo",
      apply_scope: "next_microphone_open",
    };
  }

  #effective(profile, policy) {
    return ACTIVITIES.filter((activity) => {
      const override = policy.overrides?.[activity.activity_id];
      if (override === "always_hide") return false;
      if (override === "always_show") return true;
      if (["show_all", "custom"].includes(policy.visibility_mode)) return true;
      const age = profile?.approximate_age;
      if (!age) return true;
      if (policy.visibility_mode === "hide_too_simple") {
        return activity.recommended_age_max == null || age <= activity.recommended_age_max;
      }
      if (policy.visibility_mode === "recommended_only") {
        if (activity.recommended_age_min == null && activity.recommended_age_max == null) return true;
        return (activity.recommended_age_min == null || age >= activity.recommended_age_min)
          && (activity.recommended_age_max == null || age <= activity.recommended_age_max);
      }
      return true;
    }).map((activity) => activity.activity_id);
  }
}

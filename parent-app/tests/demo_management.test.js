import test from "node:test";
import assert from "node:assert/strict";
import { DemoManagementApiClient } from "./support/demo_management_api.js";

test("test fixture advertises the complete Parent management surface", async () => {
  const api = new DemoManagementApiClient();
  const index = await api.index();
  assert.equal(index.capabilities["profiles.presentation"], true);
  assert.equal(index.capabilities["activities.install"], true);
  assert.equal(index.capabilities["activities.remove"], true);
  const activities = await api.activities();
  assert.ok(activities.some((activity) => activity.removable === true));
  assert.ok(activities.some((activity) => activity.package_trust === "built_in"));
});

test("test fixture Activity removal removes code while reporting child data preservation", async () => {
  const api = new DemoManagementApiClient();
  const removable = (await api.activities()).find((activity) => activity.removable);
  const result = await api.removeActivity(removable.activity_id);
  assert.equal(result.removed.activity_id, removable.activity_id);
  assert.equal(result.removed.profile_data_preserved, true);
  assert.equal((await api.activities()).some((activity) => activity.activity_id === removable.activity_id), false);
});

test("test fixture profile presentation round-trips", async () => {
  const api = new DemoManagementApiClient();
  await api.updateProfilePresentation("greta", { presentation: "boy" });
  const profile = (await api.profiles()).find((item) => item.profile_id === "greta");
  assert.equal(profile.presentation, "boy");
  assert.equal(profile.grammatical_gender, "masculine");
});

test("test fixture mirrors production age presets, excludes unknown ages, and canonicalizes legacy mode", async () => {
  const api = new DemoManagementApiClient();
  await api.updateProfile("greta", { approximate_age: 3 });
  const sample = (await api.activities())[0];
  api.addedActivities.push({
    ...sample,
    activity_id: "org.greia.unknown-age-fixture",
    title_key: "Unknown age fixture",
    recommended_age_min: null,
    recommended_age_max: null,
    package_trust: "parent_trusted_unsigned",
    source_id: "greia-parent-package-service",
    removable: true,
  });
  const activities = await api.activities();

  const exact = await api.updateActivityPolicy("greta", {
    visibility_mode: "recommended_only",
    difficulty_min: null,
    difficulty_max: null,
    overrides: {},
  });
  const exactIds = new Set(exact.effective_activity_ids);
  for (const activity of activities) {
    const minimum = activity.recommended_age_min;
    const maximum = activity.recommended_age_max;
    const hasAudience = minimum != null || maximum != null;
    const expected = hasAudience && (minimum == null || minimum <= 3) && (maximum == null || maximum >= 3);
    assert.equal(exactIds.has(activity.activity_id), expected, activity.activity_id);
  }

  const easier = await api.updateActivityPolicy("greta", {
    visibility_mode: "hide_too_simple",
    difficulty_min: null,
    difficulty_max: null,
    overrides: {},
  });
  assert.equal(easier.visibility_mode, "age_and_easier");
  const easierIds = new Set(easier.effective_activity_ids);
  for (const activity of activities) {
    const minimum = activity.recommended_age_min;
    const maximum = activity.recommended_age_max;
    const hasAudience = minimum != null || maximum != null;
    const expected = hasAudience && (minimum == null || minimum <= 3);
    assert.equal(easierIds.has(activity.activity_id), expected, activity.activity_id);
  }

  const explicit = await api.updateActivityPolicy("greta", {
    visibility_mode: "recommended_only",
    difficulty_min: null,
    difficulty_max: null,
    overrides: { "org.greia.unknown-age-fixture": "always_show" },
  });
  assert.ok(explicit.effective_activity_ids.includes("org.greia.unknown-age-fixture"));
});

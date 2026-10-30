import test from "node:test";
import assert from "node:assert/strict";
import { ParentAppState } from "../src/state.js";

const availableStatus = {
  state: "checked",
  check_available: true,
  prepare_available: true,
  restart_available: false,
  delivery: { job: { operation: "check", state: "checked", job_id: "a".repeat(32) }, catalog: { releases: [{ release_id: "r-1", version: "0.16.0" }] }, readiness: { available: true } },
};

function stateWith(api) {
  const state = new ParentAppState(api);
  state.publish({
    index: { capabilities: { "system.update.read": true, "system.update.check": true, "system.update.prepare": true, "system.update.restart": true } },
    systemUpdate: availableStatus,
  });
  return state;
}

test("update actions reconcile durable job status after the accepted POST", async () => {
  const calls = [];
  let refreshed = 0;
  const state = stateWith({
    checkSystemUpdate: async () => { calls.push(["check", {}]); return { job: { operation: "check", state: "checking", job_id: "b".repeat(32) } }; },
    systemUpdate: async () => { refreshed += 1; return { ...availableStatus, delivery: { ...availableStatus.delivery, job: { operation: "check", state: "checking", job_id: "b".repeat(32) } } }; },
    index: async () => ({ capabilities: { "system.update.read": true, "system.update.check": true, "system.update.prepare": true, "system.update.restart": false } }),
  });
  try {
    await state.checkSystemUpdate();
    assert.deepEqual(calls, [["check", {}]]);
    assert.equal(refreshed, 1);
    assert.equal(state.snapshot.systemUpdate.delivery.job.state, "checking");
  } finally { state.dispose(); }
});

test("prepare accepts only a release id from Greia's current device-filtered catalog", async () => {
  const calls = [];
  const state = stateWith({
    prepareSystemUpdate: async (releaseId) => { calls.push(releaseId); return { job: { operation: "prepare", state: "queued", job_id: "c".repeat(32) } }; },
    systemUpdate: async () => ({ ...availableStatus, delivery: { ...availableStatus.delivery, job: { operation: "prepare", state: "queued", job_id: "c".repeat(32) } } }),
    index: async () => ({ capabilities: { "system.update.read": true, "system.update.check": true, "system.update.prepare": true, "system.update.restart": false } }),
  });
  try {
    await assert.rejects(state.prepareSystemUpdate("arbitrary"), /cannot prepare/i);
    await state.prepareSystemUpdate("r-1");
    assert.deepEqual(calls, ["r-1"]);
  } finally { state.dispose(); }
});

test("a lost operation response still re-reads Greia's durable job", async () => {
  const accepted = { ...availableStatus, delivery: { ...availableStatus.delivery, job: { operation: "check", state: "checking", job_id: "d".repeat(32) } } };
  const state = stateWith({
    checkSystemUpdate: async () => { throw new Error("response lost"); },
    systemUpdate: async () => accepted,
    index: async () => ({ capabilities: { "system.update.read": true, "system.update.check": true, "system.update.prepare": true, "system.update.restart": false } }),
  });
  try {
    await assert.rejects(state.checkSystemUpdate(), /response lost/);
    assert.equal(state.snapshot.systemUpdate.delivery.job.job_id, "d".repeat(32));
  } finally { state.dispose(); }
});

test("check can reveal prepare and restart capabilities as cached device readiness changes", async () => {
  let nextStatus = null;
  let nextCapabilities = { "system.update.read": true, "system.update.check": true, "system.update.prepare": false, "system.update.restart": false };
  const status = (job, availability) => ({
    ...availability,
    delivery: { job, catalog: { releases: [{ release_id: "r-1", version: "0.16.0" }] }, readiness: { available: availability.prepare_available || availability.restart_available } },
  });
  const state = new ParentAppState({
    checkSystemUpdate: async () => { nextStatus = status({ operation: "check", state: "checking", job_id: "e".repeat(32) }, { check_available: true, prepare_available: false, restart_available: false }); return { job: nextStatus.delivery.job }; },
    prepareSystemUpdate: async (releaseId) => { assert.equal(releaseId, "r-1"); nextStatus = status({ operation: "prepare", state: "ready_to_restart", job_id: "f".repeat(32) }, { check_available: true, prepare_available: true, restart_available: true }); nextCapabilities = { ...nextCapabilities, "system.update.prepare": true, "system.update.restart": true }; return { job: nextStatus.delivery.job }; },
    restartSystemUpdate: async () => { nextStatus = status({ operation: "restart", state: "restart_pending", job_id: "1".repeat(32) }, { check_available: true, prepare_available: true, restart_available: false }); nextCapabilities = { ...nextCapabilities, "system.update.restart": false }; return { job: nextStatus.delivery.job }; },
    systemUpdate: async () => nextStatus,
    index: async () => ({ capabilities: nextCapabilities }),
  });
  state.publish({
    index: { capabilities: nextCapabilities },
    systemUpdate: status(null, { check_available: true, prepare_available: false, restart_available: false }),
  });
  try {
    await state.checkSystemUpdate();
    assert.equal(state.capability("system.update.prepare"), false);
    // Check completion makes the catalog/readiness available to prepare.
    nextStatus = status({ operation: "check", state: "checked", job_id: "e".repeat(32) }, { check_available: true, prepare_available: true, restart_available: false });
    nextCapabilities = { ...nextCapabilities, "system.update.prepare": true };
    await state.refreshSystemUpdate();
    assert.equal(state.capability("system.update.prepare"), true);
    await state.prepareSystemUpdate("r-1");
    assert.equal(state.capability("system.update.restart"), true);
    await state.restartSystemUpdate();
    assert.equal(state.capability("system.update.restart"), false);
    assert.equal(state.snapshot.systemUpdate.delivery.job.state, "restart_pending");
  } finally { state.dispose(); }
});

test("status polling is scheduled only for active device jobs", () => {
  const state = stateWith({});
  state.publish({ systemUpdate: { ...availableStatus, delivery: { ...availableStatus.delivery, job: { operation: "prepare", state: "downloading" } } } });
  assert.notEqual(state.systemUpdatePollTimer, null);
  state.publish({ systemUpdate: { ...availableStatus, delivery: { ...availableStatus.delivery, job: { operation: "prepare", state: "rolled_back" } } } });
  assert.equal(state.systemUpdatePollTimer, null);
  state.dispose();
});

test("authorized software package upload reconciles durable status and polls only while active", async () => {
  let nextStatus = {
    ...availableStatus,
    software_update: { available: true, restart_available: false, job: null },
  };
  const calls = [];
  const state = new ParentAppState({
    uploadSoftwareUpdatePackage: async (file) => { calls.push(file.name); return { job: { job_id: "7".repeat(32), state: "queued", restart_available: false } }; },
    systemUpdate: async () => nextStatus,
    index: async () => ({ capabilities: { "system.update.read": true, "system.update.package.install": true } }),
  });
  state.publish({
    index: { capabilities: { "system.update.read": true, "system.update.package.install": true } },
    systemUpdate: nextStatus,
  });
  try {
    await state.uploadSoftwareUpdatePackage({ name: "greia.greia_update" });
    assert.deepEqual(calls, ["greia.greia_update"]);
    nextStatus = { ...nextStatus, software_update: { available: true, restart_available: false, job: { state: "applying", package_bytes: 10, received_bytes: 10 } } };
    await state.refreshSystemUpdate();
    assert.notEqual(state.systemUpdatePollTimer, null);
    nextStatus = { ...nextStatus, software_update: { available: true, restart_available: false, job: { state: "applied" } } };
    await state.refreshSystemUpdate();
    assert.equal(state.systemUpdatePollTimer, null);
  } finally { state.dispose(); }
});

test("accepted package receipt survives a status GET failure and continues polling", async () => {
  const accepted = { job: { job_id: "9".repeat(32), state: "queued", restart_available: false } };
  const state = new ParentAppState({
    uploadSoftwareUpdatePackage: async () => accepted,
    systemUpdate: async () => { throw new Error("Greia restarted after accepting the package"); },
  });
  state.publish({
    index: { capabilities: { "system.update.read": true, "system.update.package.install": true } },
    systemUpdate: { ...availableStatus, software_update: { available: true, job: null } },
  });
  try {
    const receipt = await state.uploadSoftwareUpdatePackage({ name: "update.greia_update" });
    assert.equal(receipt.job.job_id, accepted.job.job_id);
    assert.equal(state.snapshot.systemUpdate.software_update.job.job_id, accepted.job.job_id);
    assert.notEqual(state.systemUpdatePollTimer, null);
  } finally { state.dispose(); }
});

test("lost software package POST reply reconciles and retains the device's accepted job", async () => {
  const accepted = { job: { job_id: "a".repeat(32), state: "queued", restart_available: false } };
  let refreshes = 0;
  const state = new ParentAppState({
    uploadSoftwareUpdatePackage: async () => {
      throw Object.assign(new Error("response lost after upload"), { code: "network_error", status: 0 });
    },
    systemUpdate: async () => {
      refreshes += 1;
      const job = refreshes === 1 ? null : accepted.job;
      return { ...availableStatus, software_update: { available: true, restart_available: false, job } };
    },
    index: async () => ({ capabilities: { "system.update.read": true, "system.update.package.install": true } }),
  });
  state.publish({
    index: { capabilities: { "system.update.read": true, "system.update.package.install": true } },
    systemUpdate: { ...availableStatus, software_update: { available: true, restart_available: false, job: null } },
  });
  try {
    await assert.rejects(state.uploadSoftwareUpdatePackage({ name: "update.greia_update" }), /response lost after upload/);
    assert.equal(refreshes, 1);
    assert.notEqual(state.systemUpdatePollTimer, null);

    await state.refreshSystemUpdate();
    assert.equal(refreshes, 2);
    assert.equal(state.snapshot.systemUpdate.software_update.job.job_id, accepted.job.job_id);
    assert.notEqual(state.systemUpdatePollTimer, null);
  } finally { state.dispose(); }
});

test("lost software POST reply returns the durable receipt when the first status read finds it", async () => {
  const job = { job_id: "c".repeat(32), state: "queued", restart_available: false };
  const state = new ParentAppState({
    uploadSoftwareUpdatePackage: async () => {
      throw Object.assign(new Error("response lost after durable receipt"), { code: "network_error", status: 0 });
    },
    systemUpdate: async () => ({
      ...availableStatus,
      software_update: { available: true, restart_available: false, job },
    }),
    index: async () => ({ capabilities: { "system.update.read": true, "system.update.package.install": true } }),
  });
  state.publish({
    index: { capabilities: { "system.update.read": true, "system.update.package.install": true } },
    systemUpdate: { ...availableStatus, software_update: { available: true, job: null } },
  });
  try {
    const receipt = await state.uploadSoftwareUpdatePackage({ name: "update.greia_update" });
    assert.equal(receipt.job.job_id, job.job_id);
    assert.equal(state.snapshot.systemUpdate.software_update.job.job_id, job.job_id);
    assert.notEqual(state.systemUpdatePollTimer, null);
  } finally { state.dispose(); }
});

test("malformed 2xx receipt recovers the accepted job after status reconnects", async () => {
  const acceptedJob = { job_id: "d".repeat(32), state: "queued", restart_available: false };
  let refreshes = 0;
  const state = new ParentAppState({
    uploadSoftwareUpdatePackage: async () => null,
    systemUpdate: async () => {
      refreshes += 1;
      if (refreshes === 1) throw new Error("Greia restarted before the first status read");
      return { ...availableStatus, software_update: { available: true, restart_available: false, job: acceptedJob } };
    },
    index: async () => ({ capabilities: { "system.update.read": true, "system.update.package.install": true } }),
  });
  state.publish({
    index: { capabilities: { "system.update.read": true, "system.update.package.install": true } },
    systemUpdate: { ...availableStatus, software_update: { available: true, job: null } },
  });
  try {
    await assert.rejects(state.uploadSoftwareUpdatePackage({ name: "update.greia_update" }), /valid software update job receipt/);
    assert.equal(refreshes, 1);
    assert.notEqual(state.systemUpdatePollTimer, null);

    await new Promise((resolve) => setTimeout(resolve, 2700));
    assert.equal(refreshes, 2);
    assert.equal(state.snapshot.systemUpdate.software_update.job.job_id, acceptedJob.job_id);
    assert.notEqual(state.systemUpdatePollTimer, null);
  } finally { state.dispose(); }
});

test("missing full-system restart receipt reconciles accepted restart after status reconnects", async () => {
  const job = { job_id: "e".repeat(32), package_type: "full_system", state: "ready_to_restart" };
  const state = new ParentAppState({
    restartSoftwareUpdatePackage: async () => ({ accepted: true }),
    systemUpdate: async () => {
      throw new Error("Greia restarted before the first status read");
    },
    index: async () => ({ capabilities: { "system.update.read": true, "system.update.package.install": true } }),
  });
  state.publish({
    index: { capabilities: { "system.update.read": true, "system.update.package.install": true } },
    systemUpdate: { ...availableStatus, software_update: { available: true, restart_available: true, job } },
  });
  try {
    await assert.rejects(state.restartSoftwareUpdatePackage(), /valid software update job receipt/);
    assert.notEqual(state.systemUpdatePollTimer, null);
    state.api.systemUpdate = async () => ({
      ...availableStatus,
      software_update: { available: true, restart_available: false, job },
    });
    await state.refreshSystemUpdate();
    assert.equal(state.snapshot.systemUpdate.software_update.restart_available, false);
    assert.notEqual(state.systemUpdatePollTimer, null);
  } finally { state.dispose(); }
});

test("software update receipt must contain a bounded job id and known state", async () => {
  for (const receipt of [null, {}, { job: {} }, { job: { job_id: "not-a-job", state: "queued" } }, { job: { job_id: "1".repeat(32), state: "unknown" } }]) {
    const state = new ParentAppState({
      uploadSoftwareUpdatePackage: async () => receipt,
      systemUpdate: async () => { throw new Error("status unavailable"); },
    });
    state.publish({
      index: { capabilities: { "system.update.read": true, "system.update.package.install": true } },
      systemUpdate: { ...availableStatus, software_update: { available: true, job: null } },
    });
    try {
      await assert.rejects(state.uploadSoftwareUpdatePackage({ name: "update.greia_update" }), /valid software update job receipt/);
      assert.notEqual(state.systemUpdatePollTimer, null);
    } finally { state.dispose(); }
  }
});

test("local software package validation errors do not start reconciliation polling", async () => {
  let refreshes = 0;
  const state = new ParentAppState({
    uploadSoftwareUpdatePackage: async () => { throw new TypeError("Choose a .greia_update package"); },
    systemUpdate: async () => { refreshes += 1; return availableStatus; },
  });
  state.publish({
    index: { capabilities: { "system.update.read": true, "system.update.package.install": true } },
    systemUpdate: { ...availableStatus, software_update: { available: true, job: null } },
  });
  try {
    await assert.rejects(state.uploadSoftwareUpdatePackage({ name: "update.zip" }), /greia_update/);
    assert.equal(refreshes, 1);
    assert.equal(state.systemUpdatePollTimer, null);
  } finally { state.dispose(); }
});

test("lost full-system restart reply reconciles a durable restart request", async () => {
  const job = { job_id: "b".repeat(32), package_type: "full_system", state: "ready_to_restart" };
  const state = new ParentAppState({
    restartSoftwareUpdatePackage: async () => {
      throw Object.assign(new Error("response lost after restart request"), { code: "network_error", status: 0 });
    },
    systemUpdate: async () => ({
      ...availableStatus,
      software_update: { available: true, restart_available: false, job },
    }),
    index: async () => ({ capabilities: { "system.update.read": true, "system.update.package.install": true } }),
  });
  state.publish({
    index: { capabilities: { "system.update.read": true, "system.update.package.install": true } },
    systemUpdate: { ...availableStatus, software_update: { available: true, restart_available: true, job } },
  });
  try {
    const receipt = await state.restartSoftwareUpdatePackage();
    assert.equal(receipt.job.job_id, job.job_id);
    assert.equal(state.snapshot.systemUpdate.software_update.restart_available, false);
    assert.notEqual(state.systemUpdatePollTimer, null);
  } finally { state.dispose(); }
});

test("full-system package restart requires the device's ready status and separate capability", async () => {
  const calls = [];
  const job = { job_id: "f".repeat(32), package_type: "full_system", state: "restarting", restart_available: false };
  const state = new ParentAppState({
    restartSoftwareUpdatePackage: async () => { calls.push("restart"); return { job }; },
    systemUpdate: async () => ({ ...availableStatus, software_update: { available: true, restart_available: false, job } }),
    index: async () => ({ capabilities: { "system.update.read": true, "system.update.package.install": true } }),
  });
  state.publish({
    index: { capabilities: { "system.update.read": true, "system.update.package.install": true } },
    systemUpdate: { ...availableStatus, software_update: { available: true, restart_available: true, job: { ...job, state: "ready_to_restart" } } },
  });
  try {
    await state.restartSoftwareUpdatePackage();
    assert.deepEqual(calls, ["restart"]);
    assert.equal(state.snapshot.systemUpdate.software_update.job.state, "restarting");
    assert.notEqual(state.systemUpdatePollTimer, null);
  } finally { state.dispose(); }
});

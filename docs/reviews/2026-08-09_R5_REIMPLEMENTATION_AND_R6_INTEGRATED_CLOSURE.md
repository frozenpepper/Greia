# Greia R5 reimplementation and R6 integrated source closure

**Date:** 2026-08-09
**Verified source checkout:** `7562471d868a23cd90d88b43aed2501988eb5740`
**Result:** **R0 COMPLETE; R5 SOURCE-CLOSED; R6.1/R6.2 SOURCE-CLOSED**
**Clean provider-free gate:** **194/194 PASS**

## Why this review exists

The earlier R6 source-closure audit correctly stopped when the historical post-v0.12 `src/greia_platform/history.py` authority could not be recovered. The project subsequently made an explicit engineering decision to treat that authority as a **new reviewed R5 reimplementation**, not to mislabel replacement code as recovered historical source.

This review supersedes the blocker conclusion in `docs/reviews/2026-08-09_R6_SOURCE_CLOSURE_AUDIT.md`. The earlier audit remains valid historical evidence for the state before the R5 reimplementation.

## R5 authority reimplemented

`src/greia_platform/history.py` now provides one profile-owned platform authority for:

- authoritative Activity sessions independent of Activity cooperation;
- READY/final-exit persistence and restart recovery as `platform_restart`;
- bounded local event history;
- declared-event validation and score-order authority from the manifest;
- content-bound idempotency and transactional conflicting-key rejection;
- platform-owned progression rules and reward balances;
- auditable reward ledger detail with aggregate progression retained even when detail is pruned;
- bounded logical summaries and architecture-neutral export.

SQLite is an implementation detail below `ProfileHistoryStore`. Activity processes never receive the database path or SQL access.

The reimplementation is grounded in ADR 0017, the surviving `runtime/history-policy.toml`, `runtime/progression-policy.toml`, event protocol/client/broker contracts, profile/storage contracts, and parent-summary contract.

## Integrated session/event path

The installed launcher now composes one `PlatformHistoryService` alongside PermissionBroker, RuntimeManager, and Universal Storage.

`ActivitySupervisor` creates the authoritative session record before runtime preparation, Storage open, Bubblewrap resolution, broker setup, or child creation. Launch/runtime failures close the row as `launch_failure`; platform-service/cleanup failures are distinct `platform_failure` results. READY and terminal state are persisted. Unfinished records are repaired to `platform_restart` during launcher startup.

Activity events cross only an authenticated per-session `ActivityEventBroker`. The child receives a socket and opaque session token; the Bubblewrap sandbox receives only the ephemeral broker root. Activity payloads cannot author reward values: the configured Greia progression policy is the sole reward authority.

## Parent progress boundary

The existing `ParentProgressReader` is now wired into parent status/API/UI. It exposes bounded logical reward/event/score/recent-session summaries and deliberately omits:

- history database paths;
- raw event payloads;
- idempotency keys;
- broker tokens;
- internal session IDs.

Corrupt/unavailable history degrades to `available:false`; it does not take profile, hardware, or other parent controls down.

## R4 defect found during real integration

R5 integration exposed that production `ProfileContext` lacked the `activity_storage_dir()` contract required by `ActivityStorageService`; synthetic Supervisor tests had hidden this. The production profile model now has a dedicated per-profile `storage/` namespace separate from raw Activity HOME/data, with validated per-Activity subdirectories. This fix is regression-tested.

## Package-origin defects found by complete-gate execution

The standalone Activity validator and parent server both previously constructed bundled Activity registries without explicit built-in source authority, incorrectly treating Greia packages carrying trusted legacy aliases as external/developer packages. Both call sites now use explicit `ActivitySource(..., PackageTrust.BUILT_IN, "greia-system")`. Negative validation proves an external copy of the same package is not promoted to built-in trust.

## R6 integrated result

The R5 restoration removes the last source-continuity blocker underneath R6. The installed composition now proves the complete common path:

- trusted package registration → PermissionBroker authority;
- shared semantic Device Capability Service → permission and runtime compatibility;
- snapshot-bound launch coherence;
- runtime-neutral RuntimeManager/adapter command, lifecycle transport, handle, exit, force-stop and cleanup;
- platform-owned Universal Storage broker;
- platform-owned Session/Event/Progression/Reward authority;
- generic Supervisor orchestration with no Python process/READY-marker implementation leakage.

R6.1 and R6.2 are therefore **source-closed**. This does not claim direct DRM/KMS, Acer physical acceptance, Pi support, or release certification; those evidence obligations remain in R7, R8 and R14.

## Final clean-clone evidence

Permanent read-only GitHub clean verifier on checkout `7562471d868a23cd90d88b43aed2501988eb5740`:

```text
tracked files: 318
tracked PNGs: 123
git worktree: clean
Python compile: PASS
R5 architecture invariants: PASS
R6 architecture invariants: PASS
provider-free unit tests: 194 / 194 PASS
project validation: PASS
bundled Activity validation: PASS (2 / 2)
source/shell/footprint gate: PASS
```

The permanent verifier is now read-only and contains both R5 and R6 source invariants.

## Closure classification

```text
R0 continuity/canonical repository: COMPLETE
R1–R4 source safety spine: present and green in complete source gate
R5 sessions/events/progression/rewards: SOURCE-CLOSED (new reviewed reimplementation)
R6.1 Device Capability/HAL: SOURCE-CLOSED
R6.2 Runtime Adapter integration: SOURCE-CLOSED
hardware/direct-graphics certification: NOT CLAIMED
next blocking phase: R7 direct Greia graphics/session architecture
```

## Key commits

```text
0cfb82aa89df5ebc9c03a01061ebd8da82f8f4dd  reimplement History/Progression authority
b89906cc5b3a6d01e87dd6177838976dd001f500  trust-aware standalone Activity validation tests
5bd867c9488fcd61a598813cdf7a42c396ec3b2c  repair real ProfileContext storage namespace
e790a36e36b845d0a9d0ecf057180ffd3a213af3  integrate authoritative sessions and event broker
2819f73dcc57c3b69d002532c03f5d2021e7c10f  close launch-failure rows and parent progress boundary
7562471d868a23cd90d88b43aed2501988eb5740  permanent R5/R6 clean-clone invariants
```

## Next exact work

Begin R7 with an inventory of every current X11/display/input assumption before implementing direct graphics. Classify `DISPLAY`, Xauthority, XShm, `xinput`, `xrandr`, Xorg package/config/service/session dependencies and launcher/Pygame/SDL assumptions. Keep the existing R6 Display/Input interfaces stable and do not deepen X11 while building the direct DRM/KMS/KMSDRM path.

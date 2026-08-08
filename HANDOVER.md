# Greia — Standalone Handover

**Date:** 2026-08-08  
**Version:** `0.13.0-phase0-dev`  
**State:** active remediation plan audited and corrected; fresh source verification 141/141 passing; R0 reopened for canonical GitHub completeness; R1 per-Activity isolation patch exists but trusted PermissionBroker/package-origin authority remains incomplete; R2+ not implemented.

## 1. Mandatory active plan

The authoritative implementation plan is:

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

The audit/correction record is:

`docs/reviews/2026-08-08_ACTIVE_PLAN_AUDIT_AND_CORRECTION.md`

`AGENTS.md` requires future implementation sessions to read the plan, resume the first incomplete blocking phase, append progress, update this handover, run verification, and remove the active-plan reference only after full closure.

## 2. Read order

1. `AGENTS.md`
2. `docs/adr/0012-platform-architecture-constitution.md`
3. `docs/adr/0013-declarative-image-profiles-and-composable-build-artifacts.md`
4. `docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md`
5. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
6. `docs/reviews/2026-08-08_ACTIVE_PLAN_AUDIT_AND_CORRECTION.md`
7. `docs/reviews/2026-08-08_ARCHITECTURE_DEEP_REVIEW_V0_13.md`
8. `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md`
9. this handover

## 3. Product/architecture invariants

- Greia is the child-facing graphical OS experience; Linux remains substrate.
- No conventional desktop/window-manager/browser-chrome/shell path is part of normal child operation.
- Activity is the universal abstraction above Python/Web/future runtimes.
- Profiles, storage, sessions, progression, rewards, package/update, backup/restore, permissions, and parent policy are platform services, not runtime-specific copies.
- ARM and legacy x86 are co-equal; Pi 400 and Pi 500 are explicit ARM references; the old Acer/Atom class remains the hard low-resource reference.
- Xorg is a provisional migration/evidence implementation, not the target architecture; direct DRM/KMS-first appliance graphics remains the target.
- Child data must be architecture-neutral and portable.
- Parent authority is separate and typed/bounded.
- Removable media is never autorun.
- Global reward economics belong to Greia, not Activity packages.

## 4. Audit correction: discard the generic Resource Service idea

A previous chat reply proposed a generic `Resource Service`. That was not in the architecture or plan and has been explicitly rejected.

Responsibilities remain where the constitution places them:

- durable Activity files/blobs → Storage Service;
- static/package assets → Asset API/package;
- removable media → Removable Media Service;
- temporary runtime state → Runtime Adapter/session;
- package staging/cache → Package Manager;
- hardware availability → Device Capability/HAL.

Do not reintroduce a generic Resource Service without a future ADR proving a real unowned responsibility.

## 5. Fresh verification

A fresh local run on 2026-08-08:

```bash
make verify
```

passed:

- **141 / 141 unit tests**;
- project/runtime/Activity/asset validation;
- bundled Activity validation;
- existing build/system-overlay source gates;
- source footprint approximately 15 MiB.

This is source evidence only. It does not prove installed Bubblewrap behavior, image boot, DRM/KMS behavior, Acer behavior, Pi behavior, Web runtime behavior, or memory/footprint certification.

## 6. Current truthful R0 state — REOPENED / INCOMPLETE

Plan/AGENTS/HANDOVER governance exists and source verification passes.

However, GitHub is not yet a complete canonical working tree. During the plan audit, a direct GitHub fetch of:

`assets/icons/core/v1/128/unicorn.png`

returned 404 while the file exists in the current working tree and is used by the asset catalogue/tests.

Therefore future work must not claim canonical repository completeness until required binary assets are in GitHub or an explicit repository-managed external-asset mechanism exists.

## 7. Current truthful R1 state — STARTED / INCOMPLETE

### Real source improvements already present

`src/greia_launcher/supervisor.py` contains:

- immutable `ActivityAuthority`;
- installed Bubblewrap binding only the current Activity's data namespace writable at `/run/greia-activity-data`;
- no writable whole-profile bind;
- profile/platform roots hidden;
- narrow customization bind for the trusted settings Activity;
- `/media/greia` hidden when media access is absent;
- per-Activity environment/Home/XDG scope.

Additional source/tests provide:

- avatar request inside the requesting Activity data namespace;
- launcher consumption limited to the profile-management Activity path;
- negative test showing forged `GREIA_ACTIVITY_CAPABILITIES` cannot expand the current sandbox mount shape;
- missing Bubblewrap remains fail closed.

### Why R1 is NOT closed

ADR 0012 requires an effective PermissionBroker model. The current implementation still has two provisional weaknesses:

1. `ActivityAuthority.from_manifest()` derives authority from manifest fields after validation;
2. privileged manifest capabilities are currently protected by an Activity-ID allowlist.

That is not sufficient for the future `.greiaactivity` ecosystem. An external package must not acquire system privilege by claiming a reserved ID.

R1 must therefore add:

- package trust/origin tiers;
- platform `PermissionBroker` / effective-grant calculation;
- grant inputs: package trust/origin + manifest request + runtime/hardware capability + build policy + parent policy + platform security policy;
- supervisor consumes platform-issued effective grants rather than deriving privilege directly from manifest fields;
- reserved-ID/package-origin spoof negative tests;
- fabricated-manifest/effective-grant bypass negative tests.

The manifest's current `runtime.capabilities` field is also semantically overloaded. R3 will formally split capability requirements from permission requests, but R1 must already ensure requests do not self-grant privilege.

## 8. Corrected plan architecture

Blocking spine:

```text
R0 canonical repository/governance
 ↓
R1 PermissionBroker/trust/per-Activity authority
 ↓
R2 runtime-neutral lifecycle + minimal session/adapter seam
 ↓
R3 stable IDs + capability/permission/event manifest semantics
 ↓
R4 universal storage
 ↓
R5 sessions/events/progression
 ↓
R6 Device Capability/HAL + full runtime integration
```

After R6, the plan allows explicit parallel tracks:

- R7 direct graphics/session → R8 Pi 400/500 image + ARM graphics evidence;
- R9 Web runtime;
- R10 `.greiaactivity`;
- R11 `.greiabackup` once R4/R5 are ready;
- R12 parent-management integration;
- R13 boot/recovery continuity;
- R13B signed rollback-safe Greia OS/runtime updates + preserve-profile recovery;
- R14 final multi-architecture certification.

## 9. Important corrections made by the audit

- A real PermissionBroker/trust-origin model is now required in R1.
- Capability availability, permission request, and effective grant are distinct concepts.
- Minimal runtime lifecycle seam is introduced in R2 rather than deferring all abstraction to R6.
- Permanent Activity IDs are settled/migrated in R3 before durable state depends on them.
- R4 now explicitly prevents raw filesystem access from becoming a parallel save system that bypasses quota/migration/backup semantics.
- R6 now includes Device Capability Service and HAL protocols.
- R7/R8 evidence requirements are no longer circular: R7 closes x86/VM direct architecture; R8 closes Pi-specific evidence.
- Trusted broker foundations begin in R1; R12 is later integration, not the first privileged broker.
- R10 includes package trust/origin so external packages cannot spoof system privilege.
- R13B adds production Greia OS/runtime update and preserve-profile recovery work.
- R0 now requires real canonical GitHub completeness.

## 10. Next exact step

Do not start R2 yet.

1. make GitHub sufficient to reproduce the current build/test tree, including required binary assets;
2. finish R1 with a trusted PermissionBroker/effective-grant model and package-origin trust;
3. add reserved-ID/package-origin spoof tests and fabricated-manifest authority tests;
4. run `make verify`;
5. append R0/R1 progress to the active plan and update this handover;
6. commit coherent changes;
7. only then begin R2 lifecycle/watchdog work.

## 11. Evidence discipline

Source tests do not prove hardware behavior. Keep these explicitly UNPROVEN until appropriate evidence exists:

- Linux Bubblewrap execution of new R1 mount/grant shape;
- direct DRM/KMS path;
- Acer boot/install/resource behavior;
- Pi 400/500 image/boot/display/input/audio behavior;
- Web runtime footprint/performance;
- installed sub-1-GiB C0 target;
- no-visible-Linux frame-by-frame boot/failure behavior.

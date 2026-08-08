# Greia Active Plan Audit and Correction

**Date:** 2026-08-08  
**Scope:** `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` audited against ADR 0012, ADR 0013, ADR 0014, current source, current GitHub state, and a fresh source verification run.  
**Status:** complete; corrections applied to the active plan.

## 1. Why this audit exists

A previous assistant reply contradicted the actual working capabilities and also proposed a generic `Resource Service` that was not present in the Greia architecture or active plan. Because the active plan is intended to guide future sessions, the correct response is to re-audit the plan from primary project sources instead of relying on conversational continuity.

This audit therefore distinguishes:

1. what is genuinely present in the active plan;
2. what is genuinely present in source and GitHub;
3. what is still provisional or unimplemented;
4. what was invented in conversation and must be discarded;
5. structural corrections required before further implementation.

## 2. Facts independently re-verified

### 2.1 The active plan is real

The canonical path is:

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

`AGENTS.md` explicitly names it as the mandatory active implementation plan and requires progress logging, handover updates, ordered resumption, and removal of the special reference only after final plan completion.

### 2.2 The first R1 source work is real

Current source contains:

- immutable `ActivityAuthority` in `src/greia_launcher/supervisor.py`;
- per-Activity writable bind at `/run/greia-activity-data`;
- no writable bind of the whole active profile root;
- conditional narrow customization bind for the trusted settings Activity;
- `/media/greia` hidden when removable-media access is not granted;
- SDK environment capability values treated as descriptive rather than sufficient to change the sandbox command;
- avatar-change request state inside the requesting Activity data namespace.

### 2.3 The current source verification is real

A fresh run of:

```bash
make verify
```

completed successfully with:

- **141 / 141 unit tests PASS**;
- project/runtime/Activity/asset validation PASS;
- source footprint check PASS (~15 MiB source tree).

This is source evidence only, not installed Linux/Bubblewrap/physical-hardware evidence.

### 2.4 GitHub is not yet a complete canonical working tree

A direct GitHub fetch of:

`assets/icons/core/v1/128/unicorn.png`

returned 404 during this audit, while that asset exists in the current working tree and is required by the asset catalogue/tests.

Therefore the statement “GitHub is the canonical source of truth” is an intended repository contract, but **canonical completeness is not yet achieved**. This is now an R0 closure requirement.

## 3. Explicit retraction: generic `Resource Service`

The previous chat reply proposed adding a generic `Resource Service` responsible for mounted files, temporary folders, imported assets, screenshots, thumbnails, caches, and runtime resources.

That proposal is rejected.

It is not in ADR 0012 and it would blur responsibilities already assigned to existing architecture:

- durable Activity files/blobs → `ActivityStorage` / Storage Service;
- packaged/static assets → Asset API / package content;
- removable media → Removable Media Service;
- temporary/runtime files → Runtime Adapter/session sandbox;
- package staging/cache → Package Manager;
- thumbnails/artwork → owning platform service or Activity storage, depending on authority;
- hardware/resource availability → HAL / Device Capability Service.

A generic Resource Service would risk becoming a vague cross-cutting “god service”. Do not add it unless a future ADR identifies a concrete responsibility that is not already owned elsewhere.

## 4. Plan strengths confirmed

The overall risk ordering is sound:

1. authority/isolation before ecosystem expansion;
2. lifecycle/watchdog before relying on Activities for safe return;
3. durable manifest/storage/session semantics before package/backup scale-out;
4. runtime abstraction before Web;
5. direct graphics and ARM as first-class architecture work rather than afterthoughts;
6. package/update and backup as platform services rather than Parent HTTP-handler logic;
7. final evidence/certification separated from source claims.

The plan correctly preserves old-hardware resource discipline and does not assume source tests prove Acer/Pi behavior.

## 5. Corrections required and applied

### C-01 — Effective permission grants need a real PermissionBroker

**Problem:** The first R1 implementation derives `ActivityAuthority` from `manifest.capabilities`. The registry does validate privileged capabilities and restricts them to an allowlisted Activity ID, but this is still weaker than ADR 0012.

ADR 0012 explicitly requires effective grants to be computed from:

```text
manifest request
∩ runtime capability
∩ hardware capability
∩ build-profile policy
∩ parent policy
∩ platform security policy
```

Additionally, an external package must not obtain system privilege merely by claiming a reserved Activity ID.

**Correction:** R1 now requires a trusted PermissionBroker/effective-grant object with package trust/origin as an input. `ActivityAuthority.from_manifest()` is explicitly provisional and cannot close R1.

### C-02 — Capabilities and permissions must be distinct

**Problem:** The current prototype `runtime.capabilities` list mixes requirements such as `display`, `pointer`, `audio.basic` with privilege requests such as `customization.manage`, `profile.manage_own`, and `removable_media.read`.

ADR 0012 says capability and permission are different concepts.

**Correction:** R3 now explicitly splits capability requirements from permission requests and migrates the prototype schema.

### C-03 — Permanent Activity IDs must be settled before durable data

**Problem:** Storage, sessions, progression, package updates and backups all key data by Activity ID, but current built-ins still use prototype IDs such as `shape_garden`.

**Correction:** R3 now requires permanent Activity-ID policy/migration before R4/R5 persist durable state.

### C-04 — Lifecycle and runtime-adapter ordering was inconsistent

**Problem:** R2 required a runtime-neutral READY/STOP/TERMINATE lifecycle, but the runtime-adapter seam was deferred to R6. That invites a Python-specific lifecycle implementation followed by a rewrite.

**Correction:** R2 now introduces the minimal runtime lifecycle/session protocol immediately. R6 later completes runtime-specific validation/selection integration rather than recreating lifecycle.

### C-05 — Device Capability Service / HAL authority was missing

**Problem:** The plan moved toward graphics, Pi and Web without explicitly implementing ADR 0012's Device Capability Service and semantic HAL authority.

**Correction:** R6 now includes Device Capability Service plus typed Display/Input/Audio/Removable Media/Power/Network protocols before direct graphics/Pi/Web compatibility work is considered mature.

### C-06 — R7/R8 evidence dependency was partially circular

**Problem:** Direct graphics could be interpreted as needing all reference-device physical evidence before R7 closed, but Pi images required by that evidence were not implemented until R8.

**Correction:** R7 closes architecture plus x86/VM evidence; R8 provides Pi image/boot implementation and ARM direct-display/input/audio evidence. R14 remains cross-family final certification.

### C-07 — Parent broker authority appeared too late

**Problem:** The original R12 phase could be read as introducing privileged parent authority only after Package/Backup work, encouraging those services to create direct root-operation paths first.

**Correction:** trusted PermissionBroker/broker foundations begin in R1. R12 is now the consolidation/integration of package, backup, hardware, network and recovery operations into the typed parent authority surface.

### C-08 — Storage needed a policy for raw direct filesystem access

**Problem:** A universal storage API cannot reliably own quotas, migration snapshots and cross-runtime backup semantics if Python Activities can treat an unrestricted HOME tree as an alternate authoritative save API indefinitely.

**Correction:** R4 now requires a transition rule: authoritative portable saves increasingly use `ActivityStorage`; any remaining direct filesystem area is explicitly private-file compatibility/storage and cannot bypass quota/migration/backup policy.

### C-09 — Package trust state must protect privileged system Activities

**Problem:** Future `.greiaactivity` imports make an ID-only privileged allowlist dangerous.

**Correction:** R10 now requires explicit package trust/origin states and forbids external packages from acquiring built-in/system privilege merely by claiming an ID.

### C-10 — OS/runtime update and preserve-profile recovery were missing

**Problem:** A plan titled “Platform Completion” included Activity updates but omitted ADR 0012's signed, rollback-safe OS/runtime update path and preserve-profile recovery install.

**Correction:** R13B now covers signed system update artifacts/metadata, rollback-safe activation, boot health, offline bundles, and preserve-profile recovery.

### C-11 — GitHub continuity must be real, not aspirational

**Problem:** Future sessions are instructed to use GitHub as canonical source, but binary assets are currently absent remotely.

**Correction:** R0 is not considered administratively complete until the complete build/test tree is in GitHub or a documented repository-managed external-asset mechanism exists.

## 6. Corrected high-level dependency model

```text
R0 canonical repository + governance
 ↓
R1 trust / PermissionBroker / per-Activity authority
 ↓
R2 runtime-neutral lifecycle session seam
 ↓
R3 stable IDs + capability/permission/event manifest semantics
 ↓
R4 universal storage
 ↓
R5 sessions/events/progression
 ↓
R6 Device Capability/HAL + full runtime integration
 ├→ R7 direct graphics/session → R8 Pi board/image + ARM graphics evidence
 ├→ R9 Web runtime
 └→ R10 .greiaactivity

R4 + R5 → R11 .greiabackup
R1 + R6 + R10 + R11 → R12 parent authority integration
R7 + R12 → R13 boot/recovery
R11 + R12 → R13B OS/runtime update + preserve-profile recovery
all → R14 certification
```

## 7. Current truthful status after audit

### R0

**Not fully closed.** Governance/plan wiring is done, source verification passes, but canonical GitHub completeness is false while required binary assets are missing.

### R1

**Started, useful first patch landed, not closed.**

Real improvements:

- per-Activity writable namespace;
- no whole-profile writable mount;
- forged capability environment cannot expand current sandbox shape;
- scoped avatar request path;
- full source tests pass.

Still missing before R1 closure:

- PermissionBroker/effective grant calculation;
- package trust/origin model for system privilege;
- capability-vs-permission semantics (schema split is R3, but R1 must already avoid self-grant authority);
- negative test for a non-system package spoofing a privileged Activity ID;
- negative test showing a fabricated manifest object cannot mint authority;
- Linux Bubblewrap evidence remains later/final evidence.

### R2 and later

Not implemented yet.

## 8. Immediate next step

Do **not** add the previously invented Resource Service and do not begin R2 yet.

The next exact work should be:

1. complete R0 canonical GitHub continuity, including required binary assets;
2. finish R1 trust/PermissionBroker authority so the supervisor consumes a platform-issued effective grant rather than deriving privilege directly from manifest fields;
3. add reserved-ID/package-origin spoof tests;
4. rerun `make verify`;
5. append progress to the active plan and update `HANDOVER.md`;
6. only then proceed to R2 lifecycle work.

## 9. Conclusion

The active plan was not wholesale hallucinated. Its central architecture and risk ordering are sound, and the first R1 source patch is real and test-verified. However, the re-audit found meaningful architectural omissions and sequencing defects that would have caused later rework or weakened the trust model.

Those defects are now corrected in the active plan. The plan should be followed in its audited form from this point forward.

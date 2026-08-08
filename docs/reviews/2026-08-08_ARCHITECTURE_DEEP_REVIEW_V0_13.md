# Greia v0.13 Architecture Deep Review

**Date:** 2026-08-08  
**Scope:** Greia v0.13.0 Phase-0 source tree reviewed against ADR 0012, ADR 0013, ADR 0014, repository contracts, and the active Phase-0 plan.  
**Status:** Review complete in source; hardware/image evidence remains pending.

## Executive assessment

The v0.13 migration preserved the strongest parts of the Pip-era implementation and now aligns the repository terminology with the Greia architecture. The codebase is small, readable, typed in the important boundary objects, and generally avoids premature generalization. The declarative image-profile/package-set work is particularly strong and is already shaped for multiple runtime and hardware families.

The main architectural risk is no longer naming or code organization. It is **authority placement**. Several Phase-0 conveniences currently rely on an Activity process being trusted more than the constitution eventually allows. This is acceptable only while the Activity catalogue is tightly curated. It must be corrected before Greia claims a general `.greiaactivity` installation ecosystem or broader third-party Activity support.

The most important concrete finding is that the current Bubblewrap sandbox isolates **profiles from each other**, but does **not isolate Activities within the active profile**. The complete active profile root is writable inside the Activity namespace. That means an Activity can directly modify customization data or another Activity's data even if it lacks the manifest capability. In addition, capability checks inside `greia_platform.activity_api` are based on mutable environment variables inside the Activity process; these are useful API ergonomics but cannot be treated as a security boundary.

No release claim should be made until this authority problem, the direct-display migration, the boot-cover blocker, and the existing hardware evidence gates are resolved.

---

# 1. What is architecturally strong

## 1.1 Activity is already represented as a runtime-neutral concept

`ActivityManifest` explicitly carries `runtime_type`, API version, capabilities, metadata, education metadata, and a stable Activity ID. Image profiles separately declare enabled runtime families.

This is the correct direction: image composition and Activity identity are already independent concepts, so adding a Web runtime does not require inventing a parallel app catalogue.

**Assessment:** strong foundation.

## 1.2 Declarative image profiles are one of the best-aligned parts of the implementation

ADR 0013 is reflected in source:

- TOML build profiles rather than executable profile fragments;
- composable package sets;
- boot/display/runtime adapters represented separately;
- explicit compatibility/resource classes;
- ARM64 accepted by the schema without falsely claiming the current x86 builder supports it;
- release boot-cover eligibility controlled by an adapter registry;
- image declarations separated from observed hardware capability evidence.

This is exactly the kind of architecture needed for i386, ARM64, and future runtime combinations.

**Assessment:** keep and extend; do not replace with per-board ad-hoc builders.

## 1.3 The code does not prematurely fake ARM support

The schema understands ARM64 while the Phase-0 builder rejects ARM until a real board/image adapter exists. This is preferable to pretending GRUB-PC/MBR logic generalizes to Raspberry Pi.

ADR 0014 correctly strengthens this into a peer-platform requirement: Pi 400 and Pi 500 are explicit reference systems, not later ports.

**Assessment:** correct.

## 1.4 Profile identity is platform-owned and explicit

The launcher always selects a Greia profile rather than silently resuming a previous child. Profile data is held outside the Activity package, and theme/avatar state is profile-scoped.

The implementation already supports the product direction of multiple children sharing one machine without exposing Linux account concepts.

**Assessment:** good Phase-0 implementation.

## 1.5 Parent authority is physically separate from the child launcher

The parent HTTP surface is a distinct process/service and uses a pairing token rather than exposing parent operations through a normal child Activity. Hardware/profile/customization writes are mediated by bounded model classes rather than arbitrary shell commands.

This matches the constitution's separation of child and parent authority.

**Assessment:** directionally correct; package/backup services should continue this pattern rather than being implemented directly in request handlers.

## 1.6 Installer design remains appropriately fail-closed

The installer code preserves the earlier hardening work around target eligibility, repeated identity checks, payload verification, bounded whole-disk behavior, and graphical completion/recovery semantics.

The Greia rename did not weaken those contracts.

**Assessment:** strong; hardware evidence still required.

## 1.7 Resource discipline is real rather than aspirational

The C0 limits remain profile data and are enforced by the builder model. The codebase does not currently smuggle in a desktop environment, Electron, Node, per-Activity virtual environments, or other obvious resource multipliers.

**Assessment:** aligned with the old-hardware mission.

---

# 2. Critical / high-priority findings

## A-01 — Activity sandbox grants writable access to the whole active profile

**Severity:** HIGH  
**Architecture violated:** ADR 0012 P-04 / profile-scoped Activity storage; no duplicate authority; Activity author conformance checklist.

Current `ActivitySupervisor._sandbox_command()` binds the complete `profile.root` read-write at `/run/greia-profile`.

Consequences:

- Activity A can inspect or modify Activity B's data within the same child profile;
- a non-settings Activity can modify profile customization files directly;
- an Activity can create or alter the avatar-request file without going through the intended capability API;
- future package trust/signature policy would not repair this runtime authority leak.

The current model therefore provides **inter-profile isolation**, not **per-Activity storage isolation**.

### Required direction

The sandbox should expose only:

- the Activity's own writable data namespace;
- explicitly read-only shared assets/runtime resources;
- narrowly brokered capabilities through platform IPC/services;
- removable media only through a bounded read-only path or import broker when granted.

Privileged profile changes such as customization/avatar mutation should ideally be requests to a trusted Greia broker outside the Activity process, not direct writable binds into platform-owned profile structures.

### Acceptance condition

A test Activity without a capability must be unable to mutate:

- another Activity's state;
- profile customization;
- avatar/profile metadata;
- progression/reward/session state;
- parent/system state.

This needs both source tests and an installed Bubblewrap acceptance test.

## A-02 — Capability checks inside the Activity process are not a security boundary

**Severity:** HIGH  
**Architecture violated:** permission broker / platform authority model.

`greia_platform.activity_api._require_capability()` reads `GREIA_ACTIVITY_CAPABILITIES` from the Activity's environment. The Activity process can mutate its own environment.

Therefore this mechanism is suitable for SDK behavior and friendly error messages, but it cannot enforce privilege against a malicious or compromised Activity.

### Required direction

Move authoritative operations behind a trusted broker or IPC endpoint that receives the Activity identity from a channel the Activity cannot forge. The broker checks capabilities from the installed/validated manifest held by the platform, not from process-supplied environment state.

Environment variables may remain as convenience/context hints, but must not be the authority source.

## A-03 — No platform-owned forced-return/watchdog exists yet

**Severity:** HIGH / known Phase-0 blocker  
**Architecture violated:** universal lifecycle and safe return contract.

`ActivitySupervisor.launch()` currently blocks on `subprocess.run()`. A hung Activity can therefore retain the child session indefinitely unless the process exits or the OS externally kills it.

The constitution explicitly requires platform-owned forced termination regardless of runtime.

### Required direction

Introduce a supervised process/session object rather than a single blocking `subprocess.run()` call. It should support:

- READY handshake;
- liveness/health state;
- graceful stop;
- forced process-tree termination;
- normalized exit reason;
- future pause/checkpoint hooks;
- child-visible safe recovery back to Greia Shell.

The UX gesture remains open, but the lifecycle mechanism must be runtime-neutral.

## A-04 — Concrete reward amounts are still declared in Activity manifests

**Severity:** MEDIUM-HIGH  
**Architecture tension:** platform-owned progression/reward authority.

The current prototype manifest contains:

```toml
rewards = [
  { id = "reward.star", amount = 1 },
]
```

ADR 0012 states that Activities emit facts and Greia maps them to rewards/progression. A package declaring concrete global reward amounts risks turning package metadata into reward authority.

### Required direction

Before the Progression Engine is implemented, replace this concept with Activity-defined **events/objectives/outcomes**. For example:

```toml
[[education.events]]
id = "shape_garden.creation_completed"
kind = "completion"
```

Greia-owned progression policy can then decide whether that event grants stars, badges, discoveries, workshop items, or nothing.

Activity packages may describe educational meaning and event semantics; they should not define the global economy.

## A-05 — Runtime abstraction is explicit in metadata but still hard-coded in execution/validation

**Severity:** MEDIUM  
**Architecture status:** acceptable Phase-0 debt; should be resolved before Web implementation.

`ActivityRegistry.validate_package()` always applies Python AST/import validation and `ActivitySupervisor` is directly a Python/Bubblewrap launcher.

This is understandable while Python is the only implemented runtime, but adding Web by branching through these classes (`if runtime == ...`) would rapidly create procedural runtime sprawl.

### Required direction

Introduce a small runtime-adapter protocol when Web prototype work begins. Likely responsibilities:

- package validation;
- runtime-specific static validation;
- launch preparation;
- command/surface creation;
- SDK bridge;
- lifecycle supervision;
- cleanup.

Do **not** refactor just to satisfy naming purity; refactor at the moment the second runtime requires it.

---

# 3. Medium-priority findings

## A-06 — Universal Storage Service is not implemented yet

Activities currently receive writable HOME/XDG directories and can use ordinary files. That is sufficient for Phase-0 prototypes, but it is not yet the universal storage API described by ADR 0012.

Before portable backup/save migration work, implement a logical storage service with KV/JSON state, private file/blob storage, quotas, atomic writes/checkpoints, schema version, and migration transaction support. The backend may remain filesystem/SQLite-based; the Activity must not depend on that choice.

## A-07 — Session Service is not implemented

The supervisor returns only Activity ID and process return code. There is no durable platform session record with start, ready, end, duration, version, runtime, and normalized exit reason.

This should be added before parent progress/history features so those features do not invent their own telemetry store.

## A-08 — Progression Engine / Reward Ledger are not implemented

This is expected and explicitly deferred, but the current manifest reward field makes it important to settle the event schema first.

## A-09 — `.greiaactivity` and `.greiabackup` are architecture-only

The designs are strong, but there is no implementation yet. Parent installation from USB/SD and portable full-child backup remain major platform milestones.

The future importer should remain below a platform `PackageManager`; it should not become logic embedded directly in the parent HTTP request handler.

## A-10 — Xorg and Plymouth remain deliberately provisional

This is not a surprise defect. It remains the largest implementation/architecture gap.

Current profiles still carry `display.adapter = "xorg"`, stock Plymouth provisional cover, and an x86-only image adapter. ADR 0014 correctly forbids treating these as final Greia architecture.

The next graphics implementation should be designed across **both** low-end i386 and Pi 400/500 rather than replacing Xorg with something optimized only for one family.

## A-11 — Parent server application is beginning to aggregate several responsibilities

`ParentStatusApplication` currently orchestrates profiles, themes, hardware, health, authorization, and HTTP presentation.

At current size it is still manageable. However, Package Manager, Backup/Restore, storage administration, Wi-Fi and updates should not simply be added as more methods in this class.

Introduce explicit platform services and keep HTTP handlers thin as the parent feature set grows.

## A-12 — Current asset system is semantically sound but visually incomplete

The catalogue has stable semantic IDs and multiple raster sizes, which is good. However, the current 39-icon set is a prototype activity/icon sheet, not enough to define the Greia OS visual language.

Missing classes include Greia brand/boot assets, Professor Pip production character sheets, system/navigation icons, profile/account states, Activity state badges, parent-management icons, install/update/backup/restore/media icons, connection/power/audio/device status, recovery/error/safe-mode art, scene backgrounds/transitions, and low-resolution variants.

A dedicated inventory is defined in `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md`.

---

# 4. Concrete defect fixed during this review

The Greia identity migration left the removable-media root as `/media/pip` in runtime defaults, Bubblewrap hiding rules, systemd environment, tmpfiles configuration, and tests.

This review changes the canonical path to:

```text
/media/greia
```

This is a technical identity cleanup only; it does not change the removable-media security model.

---

# 5. Recommended implementation order after this review

1. **Authority isolation correction:** redesign Activity writable mounts and broker privileged capabilities.
2. **Forced-return/runtime lifecycle foundation:** replace blocking launch with a supervised session abstraction.
3. **Direct graphics/session prototype:** evaluate SDL DRM/KMS path and minimal surface/session ownership on Acer-class x86 and Pi 400/500.
4. **Boot-cover replacement:** align boot continuity with the direct graphics/session architecture rather than independently adding another transitional layer.
5. **Runtime adapter seam:** introduce it when the first Web prototype needs it.
6. **Universal Storage + Session Service:** establish state/session authority before building parent progress/history.
7. **Progression event schema and Reward Ledger:** remove concrete Activity-owned global reward economics.
8. **`.greiaactivity` Package Manager:** including USB/SD discovery/update classification and atomic activation.
9. **`.greiabackup` Backup/Restore:** logical portable export across i386/ARM64/amd64.
10. **Parent features:** add package, backup, Wi-Fi, update and recovery UI by delegating to those services.

This order prevents UI work or Web-runtime work from becoming coupled to security/storage shortcuts that would then need rewriting.

---

# 6. Conformance summary

| Architecture area | Current state | Assessment |
|---|---|---|
| Child shell owns experience | Implemented Phase-0 | Good |
| Explicit Greia profiles | Implemented | Good |
| Activity-first metadata | Implemented | Good |
| Declarative image composition | Implemented in source | Strong |
| i386 low-resource discipline | Enforced in profiles/source | Good, hardware evidence pending |
| ARM first-class architecture | Declared/schema seam | Correct, implementation pending |
| Runtime independence | Metadata/design only | Needs adapter seam before Web |
| Direct DRM/KMS graphics | Not implemented | Major planned gap |
| No-X11 target | Accepted ADR | Current source intentionally transitional |
| Boot-cover no-text guarantee | Not release-safe | Known blocker |
| Profile isolation | Implemented | Good |
| Per-Activity storage isolation | **Not implemented** | High-priority defect |
| Capability authority | In-process env check | High-priority defect |
| Forced return/watchdog | Not implemented | High-priority blocker |
| Universal storage | Not implemented | Planned |
| Automatic sessions | Not implemented | Planned |
| Platform progression/rewards | Not implemented | Manifest needs correction first |
| `.greiaactivity` | Spec only | Planned |
| `.greiabackup` | Spec only | Planned |
| Parent authority separation | Implemented | Good; avoid future monolith |
| Visual asset architecture | Semantic catalogue exists | Needs production inventory |

---

# 7. Verification

After the `/media/greia` correction and documentation updates:

```text
make verify
```

passes with **140 / 140 provider-free tests**, project/runtime/activity/asset validation, and the existing source/build contract checks.

This remains source evidence only.

---

# 8. Review conclusion

Greia v0.13 is a credible architecture-first foundation. The migration did not create a superficial rename over a structurally incompatible codebase; the image-profile model, profile ownership, installer hardening, resource discipline, and Activity metadata already support the new direction.

The next phase should resist the temptation to jump immediately to attractive Web activities or polished shell screens. The most important engineering correction is to make Activity authority match the constitution: **an Activity must have only its own writable state and must request privileged operations from trusted Greia services**. Once that boundary and the lifecycle supervisor are sound, direct graphics, Web, universal storage, package installation, backup/restore, and richer parent management can all be added without duplicating authority or later tearing out insecure shortcuts.
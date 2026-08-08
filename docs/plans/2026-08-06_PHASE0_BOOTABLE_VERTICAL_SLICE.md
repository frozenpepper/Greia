# Greia OS — Phase 0 Bootable Vertical Slice

**Status:** active evidence/implementation plan  
**Updated:** 2026-08-08  
**Current source version:** `0.13.0-phase0-dev`

## Goal

Produce and evidence a tiny, console-like Greia OS vertical slice that boots into the child profile picker/shell, launches curated Activities under platform supervision, preserves per-child state, exposes bounded parent management, and returns safely without exposing conventional Linux UI.

The first-generation Acer Aspire One is the hard low-resource floor. Raspberry Pi 400 and Raspberry Pi 500 are now co-equal first-class ARM reference devices, but real ARM image adapters are not yet implemented.

## Hard gates

- No visible Linux shell/desktop/login/package manager during normal child operation.
- Child profile picker appears on every boot; no silent last-user resume.
- Installed core remains below the profile hard limit (current C0: <1,000 MiB; preferred <=800 MiB).
- 768 MiB installer/runtime behavior must be measured, not inferred.
- Activity execution remains fail-closed under the platform sandbox.
- Removable media is never autorun and is never silently offered as a destructive install target.
- Do not authorize writing the Acer internal disk before the evidence gates are complete.
- ARM support must use the same Activity/profile/storage/progression/package/backup contracts as x86.
- X11/Xorg is a migration/evidence baseline only; no new architecture should deepen dependency on it.

## Completed source phases

### P0.1–P0.10 — Base vertical slice and hardening

The prototype work established and hardened the basic platform shell, profile system, settings path, Activity supervisor, installer model, boot policy, removable-media handling, recovery/security contracts, and provider-free test harness. These historical phases remain useful evidence but are not individually re-opened by the Greia identity migration.

### P0.11 — Target-identity and installer hardening — COMPLETE IN SOURCE / EVIDENCE PENDING

- installer target selection/revalidation fails closed;
- external/removable/ambiguous storage is rejected;
- payload/target identity is rechecked before destructive work;
- whole-disk installation remains graphical;
- destructive commands use argument arrays rather than shell interpolation.

### P0.12 — Boot/input/profile-sandbox hardening — COMPLETE IN SOURCE / EVIDENCE PENDING

- text consoles/getty/debug/rescue paths are suppressed/masked for the supported child path;
- bounded hardware settings and tap-to-click-off defaults are enforced;
- profile data is isolated and the launcher/parent mutation path is hardened;
- installer/live-media resource behavior is bounded for low-memory testing.

### P0.13 — Live-media identity, QEMU fidelity, and recovery completion — COMPLETE IN SOURCE / EVIDENCE PENDING

- live installer media carries a unique canonical identity;
- ambiguous live-media discovery is rejected;
- QEMU topology models a read-only installer USB plus one writable target;
- installed-target recovery code and clean completion/poweroff behavior are part of the graphical installer contract.

### P0.14 — Boot input, namespace isolation, and pre-erase power — COMPLETE IN SOURCE / EVIDENCE PENDING

- stock Plymouth is explicitly development-only/provisional because Escape/text fallback can reveal details;
- release promotion refuses the provisional boot-cover adapter;
- Bubblewrap namespace isolation is fail-closed;
- active profile is the only writable child namespace exposed to an Activity;
- installer power/target identity is rechecked immediately before destructive operations.

> **Review correction (P0.17A):** the P0.14 statement above is accurate only at the *profile-to-profile* level. The current Bubblewrap mount exposes the complete active profile root writable to the Activity, so it does not yet enforce per-Activity storage isolation inside that profile. See the v0.13 architecture review.

### P0.15 — Platform architecture constitution — COMPLETE (DESIGN / NO RUNTIME CLAIM)

ADR 0012 establishes:

- Activity as universal abstraction above runtime adapters;
- one curated Python runtime family for Phase 0;
- future Web runtime as a platform-owned adapter rather than a browser product surface;
- runtime-neutral lifecycle/SDK/storage/save migration/session/progression/permission/HAL contracts;
- open Activity-package and backup-format direction;
- ARM64 and legacy x86 as peer platform families;
- capability/resource classes rather than architecture-specific Activity ecosystems.

### P0.16 — Architecture-aligned image composition — COMPLETE IN SOURCE / IMAGE EVIDENCE PENDING

ADR 0013 establishes:

- typed TOML build profiles;
- composable package sets;
- explicit runtime families per profile;
- separate boot/display/runtime adapter declarations;
- machine-readable image-profile JSON separate from observed hardware capability;
- profile-owned resource budgets;
- ARM64 accepted by schema but refused by the x86 BIOS builder until a board/image adapter exists;
- release boot-cover eligibility controlled by an explicit adapter registry.

### P0.17 — Greia identity migration and direct-graphics architecture — COMPLETE IN SOURCE / DISPLAY MIGRATION PENDING

ADR 0014 and the v0.13 migration establish:

- project/platform identity changed from the prototype working name to **Greia**;
- technical Python namespaces, services, system paths, Unix service identities, build artifacts, environment variables, package/backup extensions, parent API branding, and current documentation use Greia naming;
- **Professor Pip** remains reserved for the child-facing character/content layer;
- Raspberry Pi 400 and Raspberry Pi 500 are explicit ARM64 reference devices and ARM is peer to legacy i386/x86;
- X11/Xorg is a temporary migration/evidence baseline, not an intended Greia architecture layer;
- target graphical direction is direct/appliance-oriented around DRM/KMS and the thinnest practical session/surface path;
- current Xorg code remains temporarily so existing hardened behavior/tests are not discarded before an evidence-backed replacement exists;
- `make verify` passes **140/140** provider-free tests after the complete identity migration.

### P0.17A — Architecture deep review and visual-system inventory — COMPLETE IN SOURCE

- v0.13 implementation reviewed against ADR 0012/0013/0014 and repository contracts;
- review recorded in `docs/reviews/2026-08-08_ARCHITECTURE_DEEP_REVIEW_V0_13.md`;
- production OS visual/character/icon/screen inventory recorded in `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md`;
- missed technical rename `/media/pip` identified and corrected to canonical `/media/greia` in the verified local source tree;
- high-priority architecture finding: Bubblewrap currently grants each Activity writable access to the full active profile root, which provides inter-profile isolation but not per-Activity storage isolation;
- high-priority architecture finding: in-process environment-variable capability checks are not a trusted authorization boundary and must become brokered platform authority before broad third-party Activity distribution;
- forced-return/watchdog remains a high-priority lifecycle blocker;
- current Activity manifest concrete reward amounts should be replaced by platform-mapped event/objective semantics before Progression Engine implementation;
- Runtime Adapter, universal Storage, Session Service, Progression/Reward Ledger, `.greiaactivity`, `.greiabackup`, direct graphics and ARM image adapters remain intentionally pending;
- `make verify` still passes **140/140** after the local path correction;
- no hardware/image evidence claims are added by this source review.

## Current implementation/evidence work

### P0.18 — Activity authority and lifecycle correction

Before a general package ecosystem or Web runtime, align runtime authority with ADR 0012.

Required work:

1. stop bind-mounting the whole active profile writable into ordinary Activity sandboxes;
2. expose only the current Activity's writable namespace;
3. move privileged profile/customization operations behind a trusted Greia broker/IPC boundary;
4. treat Activity environment capability values as convenience metadata only, never authority;
5. add negative tests proving an Activity cannot mutate another Activity's save, profile customization, avatar/profile registry, progression, parent state or system state;
6. replace blocking `subprocess.run()` Activity execution with a supervised Activity session supporting READY, liveness, graceful stop, forced process-tree termination and normalized exit reasons;
7. preserve the low-end Bubblewrap/resource constraints and fail-closed launch behavior.

### P0.19 — Direct Greia graphics/session architecture

Design and implement the replacement for the provisional Xorg path.

Required work:

1. inventory current X11-specific contracts (`xinput`, `xrandr`, X authority/socket exposure, launcher startup, Bubblewrap display sharing, installer display startup);
2. define a small platform display/input abstraction independent of Activities;
3. evaluate SDL KMSDRM/direct backends on the low-end x86 and Raspberry Pi families;
4. determine whether a tiny compositor/session broker is actually required for Web-runtime surfaces, transitions, safe crash recovery, and input routing;
5. preserve child-visible boot/shell/activity continuity and fail-safe recovery;
6. measure disk/RAM/latency relative to the provisional Xorg baseline;
7. remove Xorg package sets/services/tests only after the replacement has equivalent or stronger evidence.

**Acceptance:** no conventional desktop/display-server UI; shell and Activity lifecycle proven on required references; low-resolution/input/audio settings behavior preserved through platform APIs; resource measurements recorded.

### P0.20 — ARM64 Raspberry Pi image adapters

Add real board/image adapters below the shared profile schema for Pi 400 and Pi 500.

Required work:

- select supported Debian/Raspberry Pi base/firmware strategy;
- implement board-specific boot/image creation without leaking differences into Activity contracts;
- add typed Pi profiles only when the boot/image adapter exists;
- prove display/input/audio/network/removable-media behavior;
- verify the same profile/storage/progression/package/backup contracts as x86.

### P0.21 — Embedded Web runtime benchmark and selection

Web is a first-class architectural runtime but remains unimplemented.

Benchmark candidate embedded engines (WPE/WebKit-like family first; alternatives allowed) for incremental installed size, idle/peak RSS, startup latency, Canvas2D/SVG/JavaScript/audio behavior, optional WebGL, direct-display/session integration, i386 availability, ARM64/Pi behavior, security-update lifecycle, crash/forced-return behavior, and network-denied sandbox behavior.

Do not add a Web package set to a certified image profile before this evidence exists.

### P0.22 — Universal platform storage/session/progression implementation

Implement the constitution's logical services without runtime-specific forks:

- profile+Activity scoped storage API;
- architecture-neutral key/value and private-file storage;
- save schema/version/migration transaction support;
- automatic session records;
- normalized Activity events;
- platform-owned progression/reward ledger;
- parent-readable bounded summaries;
- backup/restore hooks.

Before implementing rewards, replace concrete Activity-owned reward amounts with Activity event/objective declarations interpreted by Greia-owned policy.

### P0.23 — `.greiaactivity` package/install/update path

Implement stable-ID packages, safe bounded import, USB/SD discovery, New/Update/Installed/Older/Incompatible/Invalid classification, staged validation, immutable versions, atomic activation, rollback, and save-preserving uninstall.

### P0.24 — `.greiabackup` portable backup/restore

Implement logical cross-architecture backup/restore for profiles, customization, saves/creations, progression/rewards, bounded session history, and installed-Activity inventory while excluding machine secrets by default. Preserve save-only namespaces for Activities absent on the destination.

## Remaining Phase 0 blockers from the existing baseline

- correct the Activity writable namespace/capability authority boundary identified in P0.17A;
- replace/patch stock Plymouth with a verified noninteractive branded-only boot-cover backend;
- real Acer inventory and one evidence-selected architecture profile;
- measured sub-1,000 MiB image build;
- QEMU USB-topology install, clean completion poweroff, media removal, and installed-target boot at exactly 768 MiB;
- non-destructive Acer USB boot and frame-by-frame no-text/no-clear-gap visual acceptance;
- measured installer peak memory during bounded SquashFS extraction;
- evidence-selected Intel driver/display path and Acer SD-reader behavior;
- platform-owned universal Activity watchdog/forced-return path;
- graphical Wi-Fi setup and parent pairing/revocation without shell access;
- graphical recovery for launcher/display/boot-service failure;
- Raspberry Pi 400/500 image/boot/display/input/audio acceptance;
- Web runtime selection/measurement.

## Stop conditions

Stop and reassess rather than layer hacks when any of these occurs:

- selected kernel/base cannot boot a reference device;
- direct display/input path cannot initialize a reference device reliably;
- C0 installed core reaches 1,000 MiB or more;
- idle shell plus base services consume more than 60% of physical RAM on the low-end reference;
- boot messages cannot be hidden without a viable graphical recovery path;
- essential hardware needs unsupported or legally undistributable firmware;
- installer media is ever offered as an installation target;
- selected-disk identity cannot be re-verified immediately before destructive operations;
- tap-to-click cannot be kept off by default on the reference touchpad;
- ARM support would require a separate Activity/profile/storage/progression ecosystem;
- Activity sandboxing would require trusting mutable Activity-controlled metadata for privileged authority.

## Evidence discipline

Source tests and architecture declarations are not hardware proof. Every build, boot, graphics, memory, installer, sandbox, Wi-Fi, Pi, or Web-runtime claim must be tied to captured evidence from the relevant target or controlled VM environment.
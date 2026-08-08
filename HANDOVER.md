# Greia — Standalone Handover

Date: 2026-08-08  
Version: `0.13.0-phase0-dev`  
State: Greia identity migration complete; architecture deep-review complete; 140/140 source tests passing after review corrections; Xorg retained only as migration baseline; direct graphics/ARM images/Web runtime/real hardware evidence pending.

## 1. Current mission

Greia is a tiny, console-like educational Linux appliance/platform for young children. Linux is the implementation substrate; the Greia graphical shell is the operating-system experience. Children select a Greia profile, enter the child world/workshop, launch Activities, return safely, and retain progress without seeing a desktop, shell, package manager, filesystem browser, browser chrome, login prompt, or normal boot text.

The first-generation Acer Aspire One remains the extreme low-resource reference floor, currently estimated but still unverified around 768 MiB RAM, 7 GB storage, and 1024×600. Raspberry Pi 400 and Raspberry Pi 500 are co-equal first-class ARM64 reference devices, not future portability targets.

## 2. Read order

Before changing implementation source:

1. `AGENTS.md` — hard product/engineering contracts.
2. `docs/architecture/GREIA_ARCHITECTURE.md` — living Greia architecture summary.
3. `docs/adr/0012-platform-architecture-constitution.md` — long-form Activity-first platform constitution.
4. `docs/adr/0013-declarative-image-profiles-and-composable-build-artifacts.md` — image/profile/package-set architecture.
5. `docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md` — Greia identity, ARM parity, and target direct-graphics direction.
6. `docs/reviews/2026-08-08_ARCHITECTURE_DEEP_REVIEW_V0_13.md` — latest implementation-vs-architecture review and newly identified authority gaps.
7. `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md` — required visual/character/icon/screen inventory.
8. `docs/plans/2026-08-06_PHASE0_BOOTABLE_VERTICAL_SLICE.md` — active implementation/evidence plan.
9. Recent hardening ADRs/review documents for boot, installer, sandbox, hardware settings, and recovery.

## 3. What changed in v0.13

v0.13 migrates the complete v0.12 source design from the Pip Kids OS working identity to **Greia** as a technical migration rather than a README-only rename.

Completed in the verified source tree:

- Python namespaces renamed to `greia_platform`, `greia_launcher`, `greia_parent`, and `greia_installer`;
- system paths migrated to Greia naming, including `/etc/greia-os`, `/var/lib/greia-profiles`, and `/opt/greia-os` conventions;
- build/runtime environment names migrated to `GREIA_*`;
- service/build artifact names migrated to Greia naming;
- Unix service identities migrated to `greiakid`, `greiapanel`, `greiaadmin`, `greiasettings`, and `greiaprofiles`;
- future package/backup extension references migrated to `.greiaactivity` and `.greiabackup`;
- future Web SDK examples use `globalThis.Greia`;
- parent API/service branding migrated to Greia;
- project docs and active evidence protocols migrated where they represent current state;
- Professor Pip references are preserved only where they genuinely refer to the child-facing character/content layer.

The architecture review also found one missed technical path from the prototype naming: the removable-media root remained `/media/pip`. The verified local source now uses `/media/greia` consistently in runtime defaults, Bubblewrap hiding rules, systemd environment, tmpfiles configuration, and tests.

## 4. Architecture decisions carried forward

### Activity is the universal abstraction

Python, Web, and future technologies are runtime adapters below one Activity contract. Profiles, installation/update, storage, saves, sessions, progression, rewards, permissions, backup/restore, and parent controls remain platform-owned and runtime-neutral.

### Python policy remains strict

Phase 0 retains one curated shared Python/Pygame environment. Activities may not create virtual environments, install packages, run pip/uv/poetry/conda/apt, vendor replacement interpreters/native dependency trees, or compile/download executable dependencies on the child machine.

### Web is a planned first-class runtime, not a browser mode

Web Activities will be packaged local content executed through a centrally maintained embedded engine. No URL bar, tabs, downloads UI, browser history, bookmarks, devtools, or arbitrary navigation are part of child mode. Network remains denied by default. No engine has been selected yet; an embedded WPE/WebKit-like engine is a candidate requiring measurement on both the low-end x86 floor and Raspberry Pi references.

### ARM and i386 are peers

Greia must not become an x86 platform later ported to ARM. ARM64 board/image adapters must sit below the same profile, Activity, storage, package, backup, progression, and parent contracts.

### X11 is not the target Greia architecture

The current hardened Xorg implementation remains in source as a temporary migration/evidence baseline only. New architecture targets an appliance-oriented direct graphics/session path around DRM/KMS and the thinnest practical surface/input layer. A tiny compositor may be adopted only if measured value justifies its cost; a conventional desktop environment/window-manager stack is not part of the design.

Do not simply delete the current Xorg path before the replacement proves equivalent or stronger behavior on the Acer and Pi reference devices.

## 5. New architecture-review findings — IMPORTANT

The deep review recorded in `docs/reviews/2026-08-08_ARCHITECTURE_DEEP_REVIEW_V0_13.md` found two authority problems that must be corrected before Greia claims a broad third-party Activity/package ecosystem.

### 5.1 Current Bubblewrap boundary is not per-Activity storage isolation

The existing sandbox binds the complete active profile root writable at `/run/greia-profile`.

This successfully hides sibling **profiles**, but an Activity can still inspect or mutate another Activity's data within the same profile and can directly reach profile-owned customization/request state.

Required correction: ordinary Activities must receive only their own writable state namespace. Profile-owned mutations must be brokered by trusted Greia services or exposed through narrower, capability-specific mounts only where proven safe.

### 5.2 `GREIA_ACTIVITY_CAPABILITIES` is not an authority source

The Activity SDK currently checks a capability list stored in the Activity process environment. The process can mutate its own environment, so this is useful API metadata but cannot be a security boundary.

Authoritative capability checks must occur outside the Activity process in a trusted broker using platform-held manifest identity.

### 5.3 Forced return/watchdog still missing

`ActivitySupervisor.launch()` remains blocking. Greia still needs a runtime-neutral supervised Activity session with READY, liveness, graceful stop, forced process-tree termination and normalized exit reason.

### 5.4 Reward manifest needs correction before Progression Engine implementation

The current prototype manifest lets an Activity declare concrete reward amounts. ADR 0012 says Activities report facts/events and Greia owns global reward economics. Replace concrete global reward declarations with objective/event semantics before the progression service is implemented.

## 6. Image architecture retained from v0.12

ADR 0013 remains accepted after rebranding:

- build profiles are typed declarative TOML;
- executable `.env` profile fragments remain removed;
- package composition is split into architectural package sets;
- runtime families are explicit in image profiles;
- boot/display/runtime adapters are distinct concerns;
- image-profile JSON describes intended composition, never observed hardware capability;
- resource thresholds are profile data;
- ARM64 is recognized by the profile schema while the current Phase 0 x86 BIOS/MBR/GRUB-PC image builder intentionally refuses to pretend it can build ARM images;
- release boot-cover eligibility belongs to an adapter registry, and stock Plymouth remains development-only/provisional.

The future direct-display adapter will supersede the current Xorg display package set through a dedicated implementation/evidence step.

## 7. Storage, sessions, progression, packages, and backup direction

The architecture constitution defines:

- durable Activity namespaces logically keyed by `(profile_id, activity_id)`;
- platform-controlled storage placement and quotas;
- architecture-neutral save formats;
- platform-transacted save migrations/rollback;
- automatic session creation independent of Activity cooperation;
- event-based progression where Activities report facts and Greia owns reward/progression authority;
- stable Activity IDs;
- one-file `.greiaactivity` packages with bounded safe extraction and staged atomic installation/update;
- USB/SD discovery that classifies New / Update / Installed / Older / Incompatible / Invalid without autorun;
- program removal separate from child-data deletion;
- portable logical `.greiabackup` exports that preserve profiles, saves, creations, progression, rewards, and inventory metadata while excluding machine secrets by default;
- restore of save-only/orphaned Activity namespaces even when the Activity is not installed on the destination machine.

## 8. Visual/art system work added

`docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md` now enumerates the production platform art required beyond the existing 39-icon seed catalogue.

It includes:

- Greia wordmark/compact emblem/boot-safe variants;
- boot, first-frame, first-run and recovery screens;
- production profile-card states and 16–24 avatar target;
- workshop/background/category/location art;
- Professor Pip base poses, facial states and lightweight animation states;
- recurring companion character state requirements;
- child navigation and Activity-state icon families;
- reward/progression visual vocabulary;
- Parent management, hardware, installer, USB/SD install/update and backup/restore icon/state families;
- error/loading/recovery illustrations;
- custom pointers and reusable interaction effects;
- low-resolution/resolution-safe requirements;
- semantic asset-state naming and staged art milestones.

Read it before creating permanent shell, installer or parent artwork.

## 9. Verification

After the architecture review and `/media/greia` source correction:

```text
make verify
```

passes with:

- **140 / 140 provider-free unit tests PASS**;
- project/runtime/activity/asset validation PASS;
- shell/build syntax and contract checks PASS through the existing source gate;
- source footprint remains approximately 15 MiB;
- no hardware/image acceptance is implied.

## 10. Current implementation order

The active plan now prioritizes:

1. Activity writable-namespace/capability-authority correction and forced-return lifecycle;
2. direct Greia DRM/KMS-first graphics/session implementation;
3. Pi 400/500 ARM64 image adapters;
4. embedded Web runtime benchmark/selection;
5. universal Storage/Session/Progression services;
6. `.greiaactivity` installation/update;
7. `.greiabackup` export/restore;
8. expansion of Parent UI through those platform services.

## 11. Important Phase 0 blockers

1. Correct the Activity writable namespace and trusted capability boundary found by the v0.13 review.
2. Replace/patch stock Plymouth with a verified noninteractive branded-only boot-cover backend.
3. Implement and prove the direct graphics/session path that will replace Xorg.
4. Exact Acer inventory and evidence-selected i386/amd64 build profile.
5. Real Linux target/live build with installed core below the selected profile's hard limit.
6. QEMU installer/installed-target acceptance at exactly 768 MiB.
7. Non-destructive Acer USB boot and frame-by-frame no-text/no-clear-gap visual acceptance.
8. Raspberry Pi 400 and Pi 500 board/image boot adapters plus display/input/audio evidence.
9. Platform-owned frozen-Activity watchdog/forced return.
10. Graphical Wi-Fi setup and parent pairing/revocation without shell access.
11. Graphical launcher/display/boot-service recovery surfaces.
12. Embedded Web engine benchmark/selection before any Web runtime package set is enabled.

**Do not authorize writing the Acer internal disk before the established evidence gates are satisfied and reviewed.**

## 12. Repository continuity

The canonical repository is `frozenpepper/Greia`. Architecture, ADRs, reviews, plans and visual-system requirements should continue to be committed there after substantive work. Chat transcripts are not the canonical specification.
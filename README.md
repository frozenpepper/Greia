# Greia OS

Status: Phase 0 source fifth-review hardened; Greia identity migration complete in the verified source tree; direct graphics, built images, and reference-hardware evidence remain pending  
Version: `0.13.0-phase0-dev`  
Date: 2026-08-08

Greia is a non-profit, open-source, Activity-first educational computing platform for young children. Linux is the implementation substrate; the Greia graphical shell is the operating-system experience. During normal child use Linux must disappear: no desktop, terminal, shell, login prompt, package manager, filesystem UI, browser chrome, or boot text may appear.

The first-generation Acer Aspire One remains the hard low-end reference device. Raspberry Pi 400 and Raspberry Pi 500 are co-equal first-class ARM reference devices rather than future ports. Current Acer estimates—still requiring hardware inventory evidence—are roughly 768 MiB RAM, 7 GB storage, and 1024×600. The preferred installed core target remains at most 800 MiB; the current builder hard-fails at 1,000 MiB or more.

## Architecture constitution

ADR 0012 (`docs/adr/0012-platform-architecture-constitution.md`) is the long-form platform constitution. It makes **Activity** the stable abstraction above replaceable runtime/display/hardware adapters, preserves one curated shared Python runtime for Phase 0, defines a future first-class Web adapter without creating a second app ecosystem, and specifies portable storage, sessions, progression, packages, backups, permissions, HAL boundaries, and multi-architecture strategy.

ADR 0014 (`docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md`) supersedes the remaining Pip-era identity and graphics ambiguity: **Xorg is retained only as a temporary Phase 0 migration/evidence baseline and is not part of the target Greia architecture.** The target graphics path is direct/appliance-oriented around DRM/KMS and the thinnest practical session/surface layer.

## Greia v0.13 migration

The complete uploaded v0.12 working tree was migrated to Greia and verified locally before this repository update.

The technical migration covers:

- Python namespaces: `greia_platform`, `greia_launcher`, `greia_parent`, `greia_installer`;
- system services, build artifacts, and technical paths using Greia naming;
- `/etc/greia-os` and `/var/lib/greia-profiles`;
- `GREIA_*` build/runtime environment variables;
- future `.greiaactivity` and `.greiabackup` formats;
- `globalThis.Greia` as the future Web SDK bridge name;
- Greia parent API/service branding;
- project documentation and evidence protocols.

**Professor Pip** remains reserved for the child-facing character/content layer. He is no longer the technical platform identity.

The migrated v0.13 tree passes:

```text
140 / 140 provider-free unit tests
project/runtime/activity/asset validation
shell syntax/contract checks
source footprint gate
```

This is source evidence only. It does not prove a Linux image, direct DRM/KMS behavior, Raspberry Pi boot support, Web runtime behavior, or physical Acer behavior.

## Core platform model

Greia is **Activity-first and runtime-agnostic**.

```text
Greia Platform
    │
    ├── Profiles / Parent policy
    ├── Storage / Sessions / Progression / Rewards
    ├── Package / Backup / Permissions
    ├── Greia Shell
    │
    └── Activity Runtime Manager
           ├── Python/Pygame
           ├── Web (planned, engine unselected)
           └── future runtimes
```

An Activity has one platform identity, manifest model, lifecycle, save namespace, progression integration, permission model, install/update path, backup behavior, and parent-policy surface. Runtime type is an implementation property.

## Graphics direction

Greia is not a Linux desktop distribution. It does not require a desktop environment, general-purpose window manager, or X11 as a product layer.

The intended architecture is approximately:

```text
Linux kernel + drivers
        ↓
DRM/KMS / GBM/EGL where appropriate
        ↓
minimal Greia display/session layer
        ↓
Greia Shell OR supervised Activity runtime
```

The hardened v0.12 Xorg path remains temporarily in source only to preserve a tested migration/evidence baseline while the direct path is designed and proven. Do not add new features that deepen X11 dependency.

## Architecture families

ARM64 and legacy x86 are peers behind common Greia contracts.

Reference families include:

- legacy i386 Atom/netbook — extreme low-resource floor;
- Raspberry Pi 400 — ARM64 reference;
- Raspberry Pi 500 — current ARM64 reference;
- modern amd64 PC — modern compatibility reference.

Activities target capabilities/resource classes, not CPU family, except when unavoidable native code makes architecture-specific packaging necessary.

## Current image architecture inherited from v0.12

ADR 0013 (`docs/adr/0013-declarative-image-profiles-and-composable-build-artifacts.md`) established:

- declarative typed TOML image profiles;
- composable architectural package sets rather than one universal list;
- explicit runtime families per image profile;
- distinct boot/display/runtime adapter declarations;
- profile-owned resource budgets;
- machine-readable image-profile declarations separate from observed hardware capabilities;
- ARM64 accepted by the profile schema but intentionally rejected by the current x86 BIOS builder until an ARM board/image adapter exists.

That source architecture is preserved by the Greia migration.

## Important Phase 0 blockers

The current baseline still must not be promoted as a finished OS image. Important open evidence/implementation gates include:

- replace stock Plymouth with a genuinely noninteractive branded-only boot cover;
- implement and measure the direct graphics/session path replacing Xorg;
- add real Raspberry Pi 400/500 boot/image adapters;
- build and measure the selected Acer target/live image;
- prove the installed core stays below its resource gate;
- prove installation and runtime behavior at exactly 768 MiB RAM;
- prove Activity sandbox/input/audio/display behavior on real targets;
- implement the platform-owned frozen-Activity watchdog/forced-return path;
- implement graphical Wi-Fi, pairing/revocation, and recovery surfaces;
- select/benchmark the embedded Web runtime before adding it to any profile.

**Do not install to the Acer internal disk until the existing evidence gates are satisfied and reviewed.**

## Repository map

- `AGENTS.md` — non-negotiable product and engineering contracts.
- `HANDOVER.md` — current standalone implementation/migration handover.
- `docs/architecture/GREIA_ARCHITECTURE.md` — Greia living architecture overview.
- `docs/adr/0012-platform-architecture-constitution.md` — long-form platform constitution inherited and rebranded from the prototype tree.
- `docs/adr/0013-declarative-image-profiles-and-composable-build-artifacts.md` — image composition/profile/package-set architecture.
- `docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md` — Greia identity, ARM parity, and direct-graphics decision.
- `docs/plans/2026-08-06_PHASE0_BOOTABLE_VERTICAL_SLICE.md` — active Phase 0 implementation/evidence plan; P0.17 records the Greia migration.
- `src/greia_platform/` — shared platform contracts and state.
- `src/greia_launcher/` — child shell/account picker and Activity supervisor.
- `src/greia_parent/` — bounded parent-management service.
- `src/greia_installer/` — graphical installer and whole-disk engine.
- `activities/` — curated dependency-free Activities.
- `build/` — image profiles, package sets, overlays, image builders, QEMU and media tooling.
- `runtime/` — curated runtime declarations and platform defaults.
- `tests/` — provider-free source/contract tests.

## Naming

- **Greia** — project/platform/ecosystem
- **Greia OS** — installable operating-system image and underlying system
- **Greia Shell** — child-facing graphical operating environment
- **Greia Parents** — parental-management surface
- **Greia SDK** — Activity-facing SDK and developer tooling
- **Professor Pip** — optional recurring child-facing guide/character

## License

Greia is intended to be non-profit and open source. A project-wide license will be selected before public release; the repository remains private during early design and implementation work.
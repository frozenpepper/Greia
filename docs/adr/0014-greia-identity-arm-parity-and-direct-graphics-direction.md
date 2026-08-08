# ADR 0014 — Greia Identity, ARM Parity, and Direct Graphics Direction

**Status:** Accepted  
**Date:** 2026-08-08  
**Supersedes/clarifies:** Pip-era product naming; ADR 0012 sections that treated Xorg as a potentially retained long-term implementation; ADR 0013 naming only.  
**Implementation state:** Full source identity migration complete; direct-graphics runtime migration not yet implemented or hardware-proven.

## Context

The project began under the working name **Pip Kids OS**. Professor Pip remains useful as a recurring child-facing character, but the platform has grown beyond one character or one workshop theme. The project is explicitly non-profit and open source.

The architecture work after ADR 0012 clarified two additional requirements:

1. ARM support is not a future port. Raspberry Pi 400 and Raspberry Pi 500-class machines are mandatory first-class reference targets alongside the legacy i386/Acer compatibility floor.
2. Greia owns the entire graphical OS/interface layer. A conventional desktop display stack is therefore not required merely because it is conventional on Linux. X11 adds a display-server layer and shared-X11 security boundary that Greia does not want as a permanent product architecture.

The existing Phase 0 implementation remains valuable evidence: it has a hardened minimal Xorg/Pygame appliance path and extensive source tests. Throwing that work away before a direct DRM/KMS replacement is measured would create risk. Keeping X11 as the intended architecture would create a different risk: accidental permanence of a layer the product does not need.

## Decision

### 1. The platform is named Greia

The project, platform, source namespaces, build artifacts, system paths, services, parent surface, and developer APIs use **Greia** naming.

Examples:

- `greia_platform`, `greia_launcher`, `greia_parent`, `greia_installer`;
- `/etc/greia-os`;
- `/var/lib/greia-profiles`;
- `.greiaactivity` and `.greiabackup`;
- `GREIA_*` build/runtime environment variables;
- `globalThis.Greia` for the future Web SDK bridge;
- system identities such as `greiakid`, `greiapanel`, `greiaadmin`, `greiasettings`, and `greiaprofiles`.

Because no public compatibility contract has shipped, the migration intentionally removes old internal Pip-prefixed technical identifiers rather than carrying aliases indefinitely.

### 2. Professor Pip remains a character, not the platform root

The proper name **Professor Pip** is preserved where it refers to the character/guide or content world. It must not be used as the technical platform identity.

### 3. ARM and i386 are peer primary platform families

Greia must be designed, built, and tested as a multi-architecture platform from the beginning.

Primary reference families include:

- legacy i386 Atom/netbook hardware, with the Acer Aspire One retained as the extreme low-resource reference floor;
- Raspberry Pi 400 / ARM64;
- Raspberry Pi 500 / ARM64;
- modern amd64 PCs.

Activity, profile, storage, progression, backup, package, parent-control, and runtime contracts remain architecture-neutral.

The current x86 BIOS image builder is one platform adapter, not the definition of Greia OS installation.

### 4. X11 is not part of the target Greia architecture

Greia's target graphical architecture is **direct/appliance-oriented**, centered on the Linux DRM/KMS graphics stack and the thinnest practical rendering/session path.

Conceptually:

```text
Linux kernel + drivers
        ↓
DRM/KMS / GBM/EGL where applicable
        ↓
Greia display/session layer
        ↓
Greia Shell OR supervised Activity runtime
```

There is no architectural requirement for X11/Xorg, a desktop environment, a general-purpose window manager, or a general-purpose compositor.

A minimal compositor may still be selected if measured evidence shows that it materially simplifies secure surface ownership, transitions, crash recovery, or Web-runtime integration at acceptable cost. Such a compositor is an implementation adapter, not a desktop environment.

### 5. Existing Xorg code is a migration baseline, not accepted final architecture

The v0.12 Xorg path remains in source temporarily because it currently carries working contracts and tests for graphical boot handoff, launcher startup, hardware settings, Bubblewrap/X11 interaction, and QEMU/Acer evidence protocols.

It must not be described as the Greia target display architecture.

A future implementation phase must replace these X11-specific paths with direct-display/input abstractions and then delete X11-specific package sets, services, xinput/xrandr assumptions, and tests once equivalent or stronger direct-backend evidence exists.

### 6. Web runtime selection follows the direct-display architecture

Greia Web Activities are not browser sessions. The future Web runtime must be an embedded, fullscreen, platform-supervised runtime that can integrate with the direct graphics/session model.

WPE WebKit or another embedded engine is a candidate, not yet a decision. Chromium is not assumed. Selection requires measured disk/RAM/performance/security/architecture evidence on at least the low-end x86 and Raspberry Pi reference families.

## Consequences

### Positive

- Platform identity no longer depends on one mascot.
- Technical names are coherent before public compatibility obligations exist.
- ARM cannot be deferred by accident.
- The graphics architecture matches the appliance model instead of inheriting desktop Linux layers.
- Runtime adapters remain independent of display implementation.
- The existing Phase 0 source stays useful as a regression/evidence baseline during migration.

### Costs and risks

- Renaming touches source namespaces, services, build scripts, tests, documentation, paths, and evidence protocols.
- Existing local scripts written for old technical names must be updated.
- Direct DRM/KMS support must be proven on old Intel hardware and Raspberry Pi reference hardware rather than assumed.
- Replacing Xorg will require reworking current xinput/xrandr hardware-control code and the current shared-X11 sandbox assumptions.
- A Web runtime cannot be finalized until the direct surface/session strategy is sufficiently concrete.

## Acceptance evidence for the identity migration

The source migration is accepted when:

- no active technical Pip-prefixed identifiers remain, excluding historical migration prose and external Python ecosystem names such as `Pipfile`;
- Professor Pip references, if present, refer only to the character/content layer;
- `make verify` passes after the rename;
- `HANDOVER.md` and the active plan describe the new Greia state.

The migrated v0.13 tree satisfies these source gates with 140/140 provider-free tests passing.

## Evidence still required for the graphics migration

Before deleting the current Xorg baseline:

- select and implement the direct display/input session path;
- prove launcher startup and Activity handoff without a desktop/display-server leak;
- prove crash recovery and forced return;
- prove low-resolution modes and input on the Acer reference hardware;
- prove Raspberry Pi 400 and Pi 500 display/input/audio behavior;
- measure memory, disk, boot time, and graphics performance against the old Xorg baseline;
- adapt parent hardware controls away from direct xinput/xrandr dependence;
- re-evaluate Activity sandbox/display isolation under the replacement stack;
- update build profiles/package sets to remove Xorg only after the replacement path is verified.
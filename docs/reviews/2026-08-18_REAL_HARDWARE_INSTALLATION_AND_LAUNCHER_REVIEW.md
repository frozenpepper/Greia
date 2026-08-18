# Real-Hardware Installation and Launcher Review — 2026-08-18

**Status:** implementation review and engineering record  
**Scope reviewed:** latest `main` through the August 18 Acer hardware tranche, installer/build contracts, systemd/Xorg/input/sandbox boot path, launcher UI foundations, Activity discovery/trust, Parent API and external Parent HTML client integration.  
**Primary goal:** convert the physical-hardware debugging sequence into hardware-independent invariants so a future build does not rediscover the same failures on another machine.

## Executive conclusion

The hardware work found real platform defects, not a collection of Acer-specific accidents. The failures fell into a small number of reusable architectural classes:

1. **build-host state was incorrectly treated as target-hardware truth**;
2. **live-media identity and installation payload were allowed to drift apart**;
3. **graphical appliance services inherited terminal semantics intended for interactive shells**;
4. **systemd/Xorg security assumptions were copied from desktop sessions although Greia owns the VT/display session directly**;
5. **legacy compatibility device nodes were treated as independent modern input devices**;
6. **sandbox mount topology was specified without first constructing the private mount targets**;
7. **a kiosk without a window manager still needs explicit keyboard focus authority**;
8. **documented hardware fixes were not all persisted into the build overlay**, so a clean rebuild could reproduce failures already solved manually;
9. **developer convenience configuration had become more permissive than the current security architecture**;
10. **Activity presentation and package installation were still too coupled to built-in assets and a flat catalogue**.

This review found the most dangerous regression in item 8: the issue log said the Xorg namespace, wrapper and legacy-input failures had been fixed, while the current build tree still contained the pre-fix values. Those build inputs have now been corrected and locked by regression tests.

## Hardware-derived platform invariants

### 1. Never derive boot-critical target drivers from the build machine

A target image is commonly assembled in a VM/chroot that exposes completely different storage hardware from the eventual laptop. Therefore host probing is not authority for the target initramfs.

Greia now carries the generic x86 root-storage stack three ways:

- `MODULES=most` in both target and live initramfs configuration;
- explicit `ahci`, `libata`, `sd_mod` module lists;
- executable `greia-storage-modules` initramfs hooks that call `manual_add_modules` for those modules.

**Rule:** any future boot-critical hardware class whose absence can make the root filesystem undiscoverable must be selected from the compatibility profile/platform contract, never solely from build-host autodetection.

### 2. Installer media is one versioned object, not a bag of files

The live kernel/initrd/squashfs, `.disk/live-uuid`, installation payload squashfs, payload digest and target-profile manifest are one coherent artifact. Hand-copying only the files that appear boot-related produced two separate real failures.

**Rule:** custom media creation must reproduce the official media contract atomically. A tool or runbook must never instruct an operator to assemble a subset from memory.

### 3. GUI processes must never inherit the VT as stdin

Greia graphical services own a VT for display/input, but that does **not** make the VT an appropriate stdin stream. Child package tools and other subprocesses can otherwise be stopped by SIGTTIN when X becomes the foreground process group.

**Rule:** graphical appliance services use `StandardInput=null`; subprocess launchers use `stdin=DEVNULL` unless an API explicitly requires supplied input. The VT is a display/session resource, not an implicit interactive shell.

### 4. Service sandboxing follows the actual display backend contract

The current R7-provisional Xorg backend opens the VT, DRM/input devices and ordinary Xorg runtime/log paths. A desktop-daemon-style mount namespace (`ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`, narrow `ReadWritePaths`) prevented the platform-owned display server from starting.

**Rule:** do not add service-hardening directives by checklist. Derive them from the exact backend authority/path/device contract and prove them on physical hardware. Activity isolation remains separate and must not be weakened merely because the display-manager service needs broader host access.

### 5. Volatile paths needed by systemd namespaces must be created by systemd

`/run` begins empty. `ExecStartPre` runs too late to create a path that systemd itself needs while constructing a service namespace.

**Rule:** service-owned volatile paths use `RuntimeDirectory=` (or another systemd pre-namespace mechanism), not an `ExecStartPre` mkdir whose success depends on the namespace already existing.

### 6. Xorg wrapper policy must match the appliance session model

`allowed_users=console` assumes a conventional console/login session. Greia's current launcher is a systemd-owned appliance session and therefore failed that desktop heuristic.

**Rule:** wrapper/session authorization must be justified by the Greia display authority, not by assumptions imported from a desktop distribution. The current provisional contract is explicit `allowed_users=anybody` + `needs_root_rights=yes`; Activity processes do not inherit this authority.

### 7. Legacy compatibility input nodes are aliases, not extra devices

Old hardware may expose a touchpad through both `event*` and `/dev/input/mouse*`. Matching both through libinput can break the physical pointer.

**Rule:** Greia's Xorg compatibility backend ignores legacy `/dev/input/mouse*` nodes and consumes the event-device path. Do not add model-name special cases for one Acer/Synaptics device.

### 8. Sandbox destinations must exist inside the sandbox filesystem

Bubblewrap cannot bind onto absent paths under a read-only root. `/run` is also semantically volatile and should be private to the Activity sandbox.

**Rule:** construct private writable/empty namespaces (`--tmpfs /run`, explicit `--dir` mount targets) before binds. Do not use user-namespace settings that remove required access to platform-owned group-readable profile sources unless the entire ownership model is redesigned together.

### 9. A window-manager-free kiosk needs explicit focus handoff

Creating a fullscreen SDL window does not guarantee X keyboard focus when there is no WM.

**Rule:** the current X11 compatibility backend explicitly focuses the launcher window. A future R7 backend must provide the equivalent semantic focus guarantee through its own backend contract.

### 10. Development access must fail closed

The review found stale builder branches that still write a known `greia/greia` password and a permissive SSH drop-in for developer profiles, even though the current supported developer provisioning architecture is key-only `greiaadmin` with root/password SSH disabled.

Immediate defense-in-depth now guarantees that stale builder text cannot make the resulting machine remotely reachable by those credentials:

- both installed and live overlays contain `00-greia-security-floor.conf`;
- password and keyboard-interactive auth are disabled;
- root login is disabled;
- authentication requires public key;
- historical `root` and `greia` remote identities are explicitly denied;
- target first boot locks the historical local bootstrap passwords.

**Follow-up:** remove the obsolete password-writing branches from the large builders themselves. The security floor makes them non-authoritative now, but dead insecure code should still be deleted rather than preserved indefinitely.

## Installation regression locks added

`tests/test_installation_hardware_regressions.py` now source-locks the reusable invariants above:

- live-media identity and payload are emitted together;
- both live and target initramfs configurations carry the generic storage stack and executable force-add hooks;
- graphical service stdin cannot be the VT and installer subprocess stdin is detached;
- launcher runtime directory creation precedes service execution;
- the current Xorg service cannot silently regain the incompatible heavy namespace;
- Xorg wrapper policy matches the appliance session;
- legacy mouse compatibility nodes remain ignored;
- Bubblewrap retains private `/run` and explicit bind targets without the broken user namespace assumptions;
- kiosk X input focus handoff remains present;
- SSH security floors remain key-only/root-disabled and first boot locks historical bootstrap passwords.

These tests are intentionally hardware-family-neutral. They protect causes, not Acer strings.

## Launcher/UI architecture review

The old launcher already bounded visible Activities into pages, but presentation policy was embedded directly in the launcher and did not use the shared UI vocabulary consistently. It also ignored manifest categories and required every icon to exist in the system-wide icon catalogue.

The new structure keeps lifecycle/security authority in `LauncherApplication` while moving richer presentation into `GreiaLauncherPresentation` and adding small reusable primitives:

- `greia_platform.ui_motion`: renderer-neutral hover/press/launch transform samples;
- `greia_platform.ui_scroll`: renderer-neutral selection-aware bounded scrolling;
- `greia_platform.pygame_effects`: shallow depth, cached shadows, raised panels and shadowed icons;
- `greia_launcher.catalogue_view`: semantic Activity category collections;
- `greia_launcher.activity_icon`: safe package-owned icon resolution;
- `greia_launcher.presentation`: launcher composition of categories, scrolling, hover, launch flourish and package icon display.

This deliberately does **not** introduce a scene graph, compositor or general animation engine. Motion is short sampled math; caches are bounded; only visible Activity tiles render.

### Activity catalogue behavior

- "All" is always the first semantic collection.
- Activities may belong to multiple categories without duplicating package state.
- category IDs come from the manifest; display names are presentation metadata.
- the visible grid is two rows, selection-aware and scrollable by keyboard and mouse wheel.
- scroll controls are rendered only when needed.
- category selection resets the visible selection/window predictably.

### Interaction behavior

- hover/keyboard emphasis adds a small lift/scale and stronger outline;
- cards/icons receive shallow cached shadows rather than expensive full-screen effects;
- launching an Activity first performs a short (~420 ms) squiggle/bounce flourish, then uses the existing authoritative launch path and its full-screen starting overlay;
- the flourish never changes permissions, focus authority, package identity or lifecycle state.

### Activity-owned icons

Built-ins remain compatible with `icon = "paint"` catalogue IDs. Portable packages may use:

```toml
icon = "package:assets/icon.png"
```

Package icon paths must be relative, contained in the Activity root, bounded in depth/length and currently PNG or WebP. This prevents an Activity manifest from turning the launcher into an arbitrary host-file reader.

## Parent Activity installation review

The architecture previously had the correct policy—Parents must not raw-copy Activity directories or run shell/package-manager commands—but no implementation. The new tranche establishes a real typed **new-install** path without claiming that the full R10 package manager is complete.

### Package service

`ActivityPackageService` accepts a bounded `.greiaactivity` ZIP whose root is the normal Activity package root (`activity.toml` at archive root). It:

1. bounds compressed request size, entry count, path length and uncompressed total;
2. rejects traversal, absolute/backslash/hidden paths, duplicate portable paths, encryption, symlinks and special files;
3. streams extraction into private staging rather than using unsafe archive extraction helpers;
4. validates the staged package through the ordinary `ActivityRegistry`, including collision/runtime/tree constraints;
5. records source/trust as `PARENT_TRUSTED_UNSIGNED` / `greia-parent-package-service`;
6. stores one read-only immutable digest-addressed version;
7. atomically renames a validated active tree into the separate Parent Activity source;
8. writes a bounded install receipt.

Existing Activity IDs are rejected. **Updates, rollback selection, removal, signatures/revocation and curated-store policy are not declared complete by this tranche.**

### Parent API and transport gate

The protocol now defines `POST /api/v1/activities/install`, but the ordinary static capability remains false. The package-aware Parent service advertises it only when explicitly owner-enabled or on a developer image marker.

That distinction is deliberate: the current Parent transport still reports `provisional-http`. Uploading executable Activity code over that transport must not silently become a release feature merely because package validation exists.

### Parent HTML client

The pinned external Parent client now:

- uploads package bytes directly with `application/vnd.greia.activity+zip`;
- exposes the file/install form only when the Greia advertises `activities.install`;
- applies the same 32 MiB request bound client-side for immediate feedback;
- shows typed server rejection messages;
- refreshes the Activity list on successful install.

The Greia build pin and integrity manifest were advanced to the exact external-client revision, including the new module.

### Launcher discovery

Parent-installed Activities are a separate `ActivitySource` with `PARENT_TRUSTED_UNSIGNED`, then flow through the same registry, permission broker, runtime manager, history service and `ActivitySupervisor` as built-ins. They are not copied into `/opt`, relabeled as built-in, or smuggled through the developer-unsigned source.

## Remaining risks / deliberately unfinished work

1. **Delete the obsolete password-writing developer branches from the builders.** They are now neutralized by an earlier SSH security floor and first-boot locking, but dead insecure code remains technical debt.
2. **Run the new Python and Parent Node tests in a real checkout.** This review was performed through the connected GitHub repository and did not invoke repository CI/Actions.
3. **Rebuild installer and target images and repeat physical boot/install acceptance.** Source contracts are materially stronger, but generated initramfs/systemd/Xorg behavior must be proven in the produced artifacts.
4. **Complete R10 update/removal/signature/rollback semantics** before making Activity installation generally available on release transports.
5. **Finish secure Parent transport/pairing** before release-enabling executable package upload.
6. **R7 remains open.** The Xorg policy here is the known-good provisional compatibility contract, not a decision to keep Xorg forever.
7. **Category display metadata/localization** should become a platform vocabulary rather than relying indefinitely on humanized manifest IDs.
8. **Accessibility/input parity:** controller/touch category navigation and pointer cursor policy should receive physical acceptance, especially on 1024×600 hardware.

## Review principle to carry forward

When physical hardware reveals a failure, the fix is not complete until all four are true:

1. the immediate machine works;
2. the authoritative build input contains the fix;
3. a hardware-independent regression/invariant prevents accidental reversal;
4. the documentation explains the *class of failure* and how future architecture should avoid it.

The August 18 review found cases where only (1) and (4) were true. This tranche specifically closes that gap for the major installation/session failures above.

# Real-Hardware Installation and Launcher Review — 2026-08-18

**Status:** implementation review and engineering record  
**Scope reviewed:** latest `main` through the August 18 Acer hardware tranche and subsequent remediation, installer/build contracts, systemd/Xorg/input/sandbox boot path, launcher UI foundations, Activity discovery/trust, Parent API and external Parent HTML client integration.  
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

A final adversarial pass also caught a subtler portability mistake in the remediation itself: the first storage-driver fix put x86-only module names in shared `initramfs-tools/modules` files. That would have solved the Acer while potentially creating a future ARM build failure. The final source keeps the shared module files architecture-neutral and makes the executable hook consult the **target kernel** before force-adding the broad x86 SATA/AHCI floor.

The same pass removed the obsolete known-password/root-SSH bootstrap from both canonical builders instead of relying forever on an SSH drop-in to neutralize dead insecure code. It also gives the Parent package store a private process-wide transaction lock so receipt preparation and Activity activation cannot race merely because the HTTP/package-service process topology changes later.

## Hardware-derived platform invariants

### 1. Never derive boot-critical target drivers from the build machine

A target image is commonly assembled in a VM/chroot that exposes completely different storage hardware from the eventual laptop. Therefore host probing is not authority for the target initramfs.

The current policy is deliberately two-layered:

- `MODULES=most` in both target and live initramfs configuration provides the broad generic driver set;
- executable `greia-storage-modules` hooks consult the **target kernel** with `modinfo -k "$version"` and conditionally `manual_add_modules` the broad x86 root-storage floor (`ahci`, `libata`, `sd_mod`) only when those modules exist.

The shared `etc/initramfs-tools/modules` files intentionally do **not** hardcode x86-only names. This prevents a legacy-x86 fix from poisoning a future ARM/board image.

**Rule:** any future boot-critical hardware class whose absence can make the root filesystem undiscoverable must be selected from the compatibility profile/target-kernel contract, never solely from build-host autodetection and never by forcing one architecture's modules through a shared overlay.

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

The review found stale builder branches that wrote a known `greia/greia` password and enabled permissive root/password SSH for developer profiles, even though the supported developer architecture was key-only `greiaadmin`.

> **2026-08-18 owner policy amendment (applied in the local-agent session after
> this review was written):** the owner explicitly changed the development
> direction. Developer/test installations must remain reachable over SSH after
> install/reboot with the predictable `greia` / `greia` login, root SSH disabled,
> and key auth retained only as an additional automation path. The paragraphs
> below describing key-only `greiaadmin` as the only developer identity reflect
> the policy that was in force when this review was written; the current
> reconciled source/docs are described in `HANDOVER.md` and
> `docs/agents/GREIA_AGENT_OPERATIONS.md`.

The source no longer carries a build-time password shortcut:

- both installed and live overlays contain `00-greia-security-floor.conf`;
- the shared floor denies `root` only and does not deny the managed `greia` account;
- base images keep `greia` password-locked and SSH disabled;
- `PermitRootLogin no` is always required;
- `build/build-image.sh` always produces a closed SSH configuration and never mints developer credentials;
- `build/build-installer-image.sh` likewise never creates a password or enables SSH, even for a developer profile;
- `build/build-developer-image.sh` is the explicit target developer path and delegates provisioning to `tools/provision_developer_image.py`;
- live-installer remote operation requires the separate `tools/provision_developer_installer.py` path.

**Rule:** a package-set/profile declaration may install prerequisites but is never credential authority. Base builders fail closed; developer reachability is an explicit provisioning operation after the closed base exists.

## Installation regression locks added

`tests/test_installation_hardware_regressions.py` now source-locks the reusable invariants above:

- live-media identity and payload are emitted together;
- live and target initramfs use `MODULES=most` plus executable target-kernel-aware force-add hooks;
- shared module files remain architecture-neutral rather than forcing x86 names everywhere;
- graphical service stdin cannot be the VT and installer subprocess stdin is detached;
- launcher runtime directory creation precedes service execution;
- the current Xorg service cannot silently regain the incompatible heavy namespace;
- Xorg wrapper policy matches the appliance session;
- legacy mouse compatibility nodes remain ignored;
- Bubblewrap retains private `/run` and explicit bind targets without the broken user namespace assumptions;
- kiosk X input focus handoff remains present;
- the canonical builders contain no known-password/root-SSH bootstrap and emit closed SSH policy;
- explicit developer target/live provisioning enables the owner-approved `greia` / `greia` development login with root denied, rather than a profile-side password shortcut;
- SSH security floors remain root-disabled; base images keep the managed `greia` account locked and SSH off.

These tests are intentionally hardware-family-neutral. They protect causes, not Acer strings.

## Launcher/UI architecture review

The old launcher already bounded visible Activities into pages, but presentation policy was embedded directly in the launcher and did not use the shared UI vocabulary consistently. It also ignored manifest navigation categories, required every icon to exist in the system-wide icon catalogue, and did not make Activity/category identity sufficiently explicit in the child UI.

The new structure keeps lifecycle/security authority in `LauncherApplication` while moving richer presentation into `GreiaLauncherPresentation` and adding small reusable primitives:

- `greia_platform.ui_motion`: renderer-neutral hover/press/launch transform samples;
- `greia_platform.ui_scroll`: renderer-neutral selection-aware bounded scrolling;
- `greia_platform.pygame_effects`: shallow depth, cached shadows, raised panels and shadowed icons;
- `greia_platform.activity_assets`: shared package-owned icon containment/header/decode validation;
- `greia_launcher.catalogue_view`: semantic Activity category collections with stable category icons;
- `greia_launcher.presentation`: launcher composition of category hierarchy, scrolling, labels, hover, launch flourish and package icon display.

This deliberately does **not** introduce a scene graph, compositor or general animation engine. Motion is short sampled math; caches are bounded; only visible Activity tiles render.

### Activity catalogue behavior

- `All` is the root/category-landing collection.
- Activities may belong to multiple launcher categories without duplicating package state.
- launcher categories are separate from education/skill metadata.
- known categories have stable semantic icons as well as titles.
- the visible grid is two rows, selection-aware and scrollable by keyboard and mouse wheel.
- scroll controls are rendered only when needed.
- category selection resets the visible selection/window predictably.
- entering a category replaces the chooser with a fixed header containing local Back, category icon and category title.
- `Esc`/`Backspace` inside a category returns to `All`; `Esc` at `All` retains the existing profile/logout behavior.

The launcher-local category Back control is not ADR-0019 Activity system chrome. It changes launcher navigation state only; it does not stop or escape a running Activity.

### Activity names are part of the tile contract

The latest real-hardware observation was that the installed launcher being exercised still showed icon-only Activity boxes. The newer repository presentation code already had a caption, but the layout treated it as an incidental line under the icon and the hardware image had not yet incorporated it.

The final source now makes this explicit rather than relying on incidental geometry:

- every Activity tile reserves a dedicated name band;
- the icon is sized into the remaining artwork region;
- labels shrink font size to fit instead of geometrically squashing glyphs;
- long names ellipsize only as a last resort;
- a package-provided icon is never sufficient identification by itself.

This must be verified on the next 1024×600 physical image; source structure alone does not prove the final typography/layout is acceptable.

### Interaction behavior

- hover/keyboard emphasis adds a small lift/scale and stronger outline;
- cards/icons receive shallow cached shadows rather than expensive full-screen effects;
- launching an Activity first performs a short (~420 ms) squiggle/bounce flourish, then uses the existing authoritative launch path and its full-screen starting overlay;
- the flourish never changes permissions, focus authority, package identity or lifecycle state.

### Activity-owned icons

Built-ins remain compatible with catalogue icon IDs. Portable packages may use:

```toml
icon = "package:assets/icon.png"
```

Package icons must be relative and contained in the Activity root. Platform validation now also bounds file size, validates supported image headers and rejects unreasonable decode dimensions before activation. This prevents an Activity manifest from turning the launcher into either an arbitrary host-file reader or a large decode-allocation trap on low-memory hardware.

## Parent Activity installation review

The architecture previously had the correct policy—Parents must not raw-copy Activity directories or run shell/package-manager commands—but no implementation. The new tranche establishes a real typed **new-install** path without claiming that the full R10 package manager is complete.

### Package service

`ActivityPackageService` accepts a bounded `.greiaactivity` ZIP whose root is the normal Activity package root (`activity.toml` at archive root). It:

1. bounds compressed request size, entry count, path length and uncompressed total;
2. rejects traversal, absolute/backslash/hidden paths, duplicate portable paths, encryption, symlinks and special files;
3. streams extraction into private staging rather than using unsafe archive extraction helpers;
4. validates the staged package through the ordinary `ActivityRegistry`, including collision/runtime/tree constraints and package-owned icon validation;
5. records source/trust as `PARENT_TRUSTED_UNSIGNED` / `greia-parent-package-service`;
6. stores one read-only immutable digest-addressed version;
7. prepares the audit metadata before activation;
8. atomically renames a validated active tree into the separate Parent Activity source as the commit point;
9. serializes the transaction process-wide with a private `0600` `.install.lock` `flock` in the authoritative package state root, with an additional in-process lock to avoid redundant local contenders.

The lock target is required to be a regular file and is opened without following symlinks where the platform exposes `O_NOFOLLOW`. Two package-service instances/processes using the same local Greia package store therefore cannot race receipt/activation bookkeeping. Any future non-local/distributed package store would require a store-appropriate equivalent rather than assuming local `flock` semantics.

Existing Activity IDs are rejected. **Updates, rollback selection, removal, signatures/revocation and curated-store policy are not declared complete by this tranche.**

### Parent API and transport gate

The protocol defines `POST /api/v1/activities/install`, but the ordinary static capability remains false. The package-aware Parent service advertises it only when explicitly owner-enabled or on a developer image marker.

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

The launcher rebuilds runtime/permission/history/supervisor authority **before** publishing a newly discovered Activity into the visible catalogue, preventing a tile from appearing with stale launch authority.

## Remaining risks / deliberately unfinished work

1. **Run the new Python and Parent Node tests in a real checkout.** This review was performed through the connected GitHub repository and did not invoke repository CI/Actions.
2. **Rebuild installer and target images and repeat physical boot/install acceptance.** Source contracts are materially stronger, but generated initramfs/systemd/Xorg behavior, fail-closed developer provisioning and the new category/name layout must be proven in produced artifacts.
3. **Complete R10 update/removal/signature/rollback semantics** before making Activity installation generally available on release transports.
4. **Finish secure Parent transport/pairing** before release-enabling executable package upload.
5. **R7 remains open.** The Xorg policy here is the known-good provisional compatibility contract, not a decision to keep Xorg forever.
6. **Category display vocabulary/localization** should become platform-owned data rather than relying indefinitely on humanized identifiers.
7. **Accessibility/input parity:** controller/touch category navigation, local Back mapping and pointer cursor policy should receive physical acceptance, especially on 1024×600 hardware.
8. **Typography/readability:** Activity label and category-header sizes must be checked with the selected Nunito Sans implementation once the font itself is actually integrated; current source still uses the existing font loader.

## Review principle to carry forward

When physical hardware reveals a failure, the fix is not complete until all four are true:

1. the immediate machine works;
2. the authoritative build input contains the fix;
3. a hardware-independent regression/invariant prevents accidental reversal;
4. the documentation explains the *class of failure* and how future architecture should avoid it.

The August 18 review found cases where only (1) and (4) were true. This tranche specifically closes that gap for the major installation/session failures above and applies the same discipline to the launcher/package work: implementation source and regression contracts exist, while physical rebuild/acceptance remains explicitly unclaimed.

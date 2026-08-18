# Greia — Standalone Engineering Handover

**Date:** 2026-08-18  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Latest reviewed implementation baseline before this handover update:** `9e6f0eb`  
**External Parent HTML revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@e30bcbcab393354b8ffb63d5829c08711d8023bd`

## Branch and execution policy

`main` is the owner-required development/integration branch. Do not create feature/recovery/work branches unless the owner explicitly changes that policy. GitHub is canonical source persistence.

Do **not** use, query, trigger, rerun, inspect or download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution. Source verification runs on an owner-controlled environment.

## Owner credential policy amendment (active since 2026-08-18)

The owner has explicitly changed the credential/SSH direction. Current policy:

1. There is **no generated random end-install password/recovery code** the parent
   must preserve. The installer completion screen reports the simple `greia` /
   `greia` login and directs the parent to Greia Parents to change it.
2. The main Parent/admin credential is `greia` / `greia`, stored only as a
   bounded PBKDF2 digest, changeable through the typed
   `/api/v1/parent-password` operation, and never returned by an API.
3. Each child may optionally have a separate Greia-profile password
   (set/replace/clear from Greia Parents); child passwords are profile-level
   Greia authentication, not one Linux account per child.
4. During active development, developer/test installs remain reachable over SSH
   as `greia` / `greia` after install and reboot. Root SSH login is disabled.
   Key authentication is retained as an additional automation path.
5. Base/release images keep `greia` locked and SSH off (fail closed).

## Evidence boundary — do not overclaim

The 2026-08-18 local-agent session ran the focused source suites and the
complete `make verify` on this checkout. Recorded executed evidence:

```text
make verify (2026-08-18, local-agent session): 663 PASS
focused 2026-08-18 suites (installation-hardware, ui-motion-scroll,
  launcher-presentation, activity-packages, activity-contract, parent-api,
  main-credential, installer-engine, installer-state, grub-security,
  developer-remote, developer-remote-snapshot): 114 PASS
Parent-App npm test at pinned e30bcbc: 10 PASS
```

A fresh installer image and physical hardware acceptance remain the next
required evidence; no new physical install/boot/launcher PASS is claimed in
this handover update.

Canonical review:

```text
docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md
```

Canonical launcher design:

```text
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

Reconciled installation issue log:

```text
docs/INSTALLATION_ISSUES_LOG.md
```

---

# 1. 2026-08-18 real-hardware installation reconciliation

The most important discovery of this review was that several fixes documented after the Acer hardware debugging were **not all persisted in authoritative build inputs**. A clean rebuild could therefore reproduce failures already solved manually. The review reconciled the build tree with the hardware-proven behavior and added hardware-independent regression locks.

## Installation lessons that are now platform invariants

1. **Build-host hardware is not target-hardware authority.** A VM/chroot cannot decide whether the target initramfs needs a boot-critical controller driver.
2. **Live-media identity and payload are one artifact.** `.disk/live-uuid`, live squashfs/kernel/initrd, installation payload, payload digest and target profile must not drift independently.
3. **A graphical VT is not interactive stdin.** GUI services use `StandardInput=null`; installer subprocesses use `stdin=DEVNULL` unless explicit input is required.
4. **Systemd namespace paths must exist before namespace construction.** Service-owned `/run` paths use `RuntimeDirectory=` rather than an `ExecStartPre` mkdir that is already too late.
5. **Display-service hardening follows the actual backend contract.** The current Xorg compatibility backend cannot be wrapped in desktop-daemon mount namespaces that block its VT/DRM/input/runtime needs.
6. **Xorg console heuristics do not describe Greia's systemd appliance session.** Current provisional wrapper policy is explicit and platform-owned.
7. **Legacy `/dev/input/mouse*` nodes are compatibility aliases, not extra modern pointer devices.** The Xorg compatibility path ignores them and consumes event devices.
8. **Bubblewrap mount destinations must be constructed inside the private filesystem before binds.** `/run` is private tmpfs; required bind targets are explicit; the previously broken user-namespace assumptions remain removed.
9. **A kiosk without a window manager still needs explicit keyboard-focus handoff.** The current X11 compatibility path uses `XSetInputFocus`.
10. **Developer access fails closed at the base and is enabled explicitly.** Base target/live builders never create usable developer passwords or enable SSH. Explicit developer provisioning (`provision_developer_image.py` / `provision_developer_installer.py`) enables the owner-approved `greia` / `greia` development login, keeps root SSH disabled, and retains an operator key as an additional automation path.
11. **A hardware fix is not complete until the machine works, the build input contains the fix, a hardware-independent regression protects the cause, and documentation explains the failure class.**
12. **A hardware fix for one architecture must not become a shared-overlay regression for another architecture.** Shared build files remain architecture-neutral; target-kernel/profile policy decides architecture-specific boot-critical modules.

## Boot/initramfs hardening — final architecture-safe form

Both installed-target and live-installer images keep:

```text
MODULES=most
```

in their Greia initramfs configuration.

They also carry executable hooks:

```text
build/overlay/etc/initramfs-tools/hooks/greia-storage-modules
build/installer-overlay/etc/initramfs-tools/hooks/greia-storage-modules
```

The hooks consult the **target kernel** rather than the build host:

```sh
for module in ahci libata sd_mod; do
    if modinfo -k "$version" "$module" >/dev/null 2>&1; then
        manual_add_modules "$module"
    fi
done
```

This preserves the broad SATA/AHCI root-storage floor on current x86 images while not forcing x86-only module names onto future ARM/board profiles.

The shared files:

```text
build/overlay/etc/initramfs-tools/modules
build/installer-overlay/etc/initramfs-tools/modules
```

are intentionally architecture-neutral and no longer contain unconditional `ahci`, `libata`, `sd_mod` lines.

`tests/test_installation_hardware_regressions.py` locks this source-level policy.

## Launcher/Xorg service reconciliation

Authoritative build inputs now preserve the hardware-proven provisional Xorg behavior:

- `RuntimeDirectory=greia-os` / mode `0755`;
- `StandardInput=null`;
- current Xorg-incompatible `ProtectSystem`, `ProtectHome`, `PrivateTmp` and restrictive `ReadWritePaths` removed from the Xorg-owning launcher service;
- `Xwrapper.config` uses `allowed_users=anybody` and `needs_root_rights=yes` for the platform-owned appliance session;
- `/dev/input/mouse*` compatibility nodes are ignored before libinput pointer/touchpad matching;
- the launcher keeps explicit X11 input-focus handoff because Greia currently has no window manager.

This is **not** a decision to retain Xorg permanently. R7 remains open and the current service configuration is the known-good compatibility contract until the selected direct/session backend is proven on hardware.

## Bubblewrap lessons persisted

The Activity sandbox now preserves the hardware-derived mount topology:

- private `--tmpfs /run`;
- explicit sandbox bind-target directories before binds;
- no previously broken `--unshare-user` / `--disable-userns` assumptions that removed access to platform-owned group-readable sources.

Do not weaken Activity isolation merely because the launcher/display service currently needs broader Xorg authority. They are different trust boundaries.

## Developer SSH path — fail-closed base, explicit greia/greia provisioning

Both target and live overlays carry `00-greia-security-floor.conf`. The shared
floor denies `root` only and does not deny the managed `greia` account; base
images keep the `greia` account password-locked and SSH off:

```text
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthenticationMethods publickey
PermitRootLogin no
DenyUsers root
```

Target first boot locks the historical root password.

The canonical builders themselves never enable SSH or mint a password:

- `build/build-image.sh` always leaves SSH disabled and emits a closed base
  configuration, including when the profile carries the `developer-remote`
  package set;
- `build/build-installer-image.sh` likewise never creates a password or enables
  SSH;
- `build/build-developer-image.sh` is the explicit target developer path and
  post-processes the closed base image via `tools/provision_developer_image.py`,
  which sets the owner-approved `greia` / `greia` development login, keeps root
  denied, installs an Ed25519 operator key as an additional automation path, and
  rewrites the security floor for the developer image before enabling SSH;
- live-installer remote operation is a separate
  `tools/provision_developer_installer.py` path that likewise enables the
  `greia` / `greia` login and keeps root SSH disabled.

`tests/test_installation_hardware_regressions.py` locks the invariant that the
canonical builders never mint credentials and that the explicit developer path
enables the owner-approved `greia` / `greia` login with root denied.

---

# 2. 2026-08-18 lightweight launcher interaction foundation

The launcher lifecycle/security core remains `LauncherApplication`. Richer child-facing presentation is composed in `GreiaLauncherPresentation`; profile/session/package/runtime/permission authority does not move into UI code.

The installed X session starts:

```text
python3 -m greia_launcher.presentation
```

Reusable layers:

```text
src/greia_platform/ui_motion.py
src/greia_platform/ui_scroll.py
src/greia_platform/pygame_effects.py
src/greia_platform/activity_assets.py
src/greia_launcher/catalogue_view.py
src/greia_launcher/presentation.py
```

## Implemented launcher behavior

- shallow cached card/icon shadows;
- bounded hover/selection lift and scale;
- stronger focus outline;
- short ~420 ms squiggle/bounce launch flourish before the existing starting overlay/authoritative launch path;
- two-row visible Activity window rather than unbounded widget creation;
- responsive two/three-column layout;
- keyboard selection keeps the selected Activity visible;
- mouse-wheel semantic-row scrolling;
- explicit scroll controls only when needed;
- bounded icon/font/shadow/decorated-icon caches;
- semantic launcher categories separate from education/skill tags;
- stable semantic category icons;
- explicit Activity names on every tile;
- persistent category identity and local Back navigation once inside a category.

The effects are deliberately cheap sampled transforms and cached surfaces, not a scene graph/compositor/general animation framework. They must remain suitable for the 1024×600/i686 resource floor.

## Activity names are now a first-class tile region

The user observed that the Acer image being exercised showed icon-only Activity boxes. The newer repository presentation already contained a caption, but it was incidental to the geometry and had not been deployed on that hardware image.

The current source now makes the name explicit:

- every Activity tile reserves a dedicated bottom name band;
- the icon is fitted into the remaining artwork region;
- font size is reduced to fit rather than geometrically squashing glyphs;
- long names use ellipsis only as a final fallback;
- the package icon is never the only way to identify an Activity.

This layout still requires real 1024×600 visual acceptance after rebuild.

## Activity navigation categories are distinct from education tags

New/updated manifests use:

```toml
[presentation]
categories = ["create", "learn"]
```

while preserving educational metadata separately:

```toml
[education]
categories = ["creativity", "geometry", "fine_motor"]
```

API-0.1 packages with no `[presentation]` table retain a compatibility fallback to educational categories; this is not the preferred new authoring pattern.

Current first-party launcher grouping:

```text
All
Create        -> Painting, Shape Garden, Writing
Learn         -> Shape Garden, Writing
My Greia      -> Workshop Settings
```

The category ordering model also understands `Play` and `Explore`.

Stable semantic category icons currently map:

```text
All       -> backpack
Create    -> palette
Play      -> puzzle_pieces
Learn     -> book
Explore   -> magnifier
My Greia  -> unicorn
```

Unknown compatibility categories use a safe generic backpack icon until the platform-owned localized category vocabulary is expanded.

## Category hierarchy / local Back

`All` is the launcher root/category landing.

At the root the available categories are presented as icon-led controls. Once a child enters a category, the chooser becomes a fixed header:

```text
[ Back ]   [ Category icon ]   Category title
```

The header remains visible while the Activity grid scrolls. This gives persistent visual context rather than requiring the child to infer a highlighted tab.

Keyboard behavior matches the hierarchy:

- `Backspace` inside a category -> `All`;
- `Esc` inside a category -> `All`;
- `Esc` at `All` -> existing logout/profile behavior;
- `Tab` still cycles categories for keyboard development/testing.

This **launcher-local Back** is not ADR-0019 Activity system chrome. It only changes launcher navigation. It does not end a running Activity and must not be confused with Greia-owned Activity Home/Back.

---

# 3. Activity-owned icons

Existing built-ins remain valid with catalogue IDs such as:

```toml
icon = "palette"
```

Portable packages can declare:

```toml
icon = "package:assets/icon.png"
```

`src/greia_platform/activity_assets.py` is the shared authority for installer and launcher validation. Package icons must be:

- relative and contained inside the Activity root;
- PNG or WebP;
- bounded in path depth/length;
- a regular file;
- bounded in bytes;
- valid enough at the image-header level to determine dimensions safely;
- within the current launcher decode bound (maximum 1024×1024).

The current package-icon file-size ceiling is 4 MiB.

Malformed/extreme package icons are rejected **before activation**, avoiding late launcher failures or large decode allocations on low-memory machines.

---

# 4. Guarded `.greiaactivity` new-install foundation

This tranche implements a real **new-install** seam, but it does **not** close R10.

Platform service:

```text
src/greia_platform/activity_packages.py
```

It accepts a bounded ZIP-based `.greiaactivity` whose `activity.toml` is at archive root and performs:

1. process-wide transaction serialization through a private `0600` `.install.lock` `flock` in the authoritative package store, plus an in-process lock to avoid redundant local contenders;
2. request/archive size and entry-count bounds;
3. traversal/absolute/backslash/hidden/portable-duplicate path rejection;
4. encryption/symlink/special-file/compression-bomb rejection;
5. streamed private staging;
6. ordinary `ActivityRegistry` validation against built-ins + installed Parent packages;
7. package-owned icon validation;
8. `PARENT_TRUSTED_UNSIGNED` provenance;
9. digest-addressed read-only immutable version storage;
10. prepared read-only active tree;
11. audit receipt preparation before activation;
12. atomic active-directory rename as the install commit point.

The lock target is required to be a regular file, is forced to mode `0600`, and is opened without following symlinks where `O_NOFOLLOW` is available. Separate `ActivityPackageService` processes sharing the same local package store therefore cannot race receipt/activation state.

Existing Activity IDs are rejected. Updates, removal, rollback selection, signatures/revocation, curated-store policy and transactional save migration are still open R10 work.

## Adversarial corrections made during implementation

Several cross-component problems were found after the first package implementation and fixed before handover:

- `/var/lib/greia-os` was previously `0750`, so `greiakid` could be unable to traverse to the Parent-installed read-only Activity source. It is now traversal-only `0755`; sensitive descendants retain their own private modes. `StateDirectoryMode=0755` migrates an existing Parent state root.
- a hot-installed Activity could initially have appeared in the catalogue without rebuilding runtime/permission/history/supervisor authority. `GreiaLauncherPresentation` now validates the new registry set and rebuilds runtime services/supervisor **before** publishing the new catalogue; failure preserves the last known-good pair.
- a receipt-write failure could otherwise have made the API report failure after executable code became visible. Receipt preparation now precedes activation, and interrupted immutable versions are digest-verified before retry reuse.
- overlapping package-service processes could otherwise race receipt/activation bookkeeping. The store now owns the transaction lock, not merely one HTTP/service object.

Any future move to a non-local/distributed package store would need a storage-appropriate equivalent rather than assuming local `flock` semantics.

---

# 5. Parent API / HTML Activity installation

Greia defines:

```text
POST /api/v1/activities/install
```

but the ordinary protocol capability remains:

```text
activities.install = false
```

`greia_parent.package_api` advertises it only when explicitly owner-enabled or on a developer image marker. This is deliberate because the current Parent transport is still provisional plaintext HTTP. **Release images do not gain executable package upload merely because the typed package service exists.**

`greia-parent.service` starts the package-aware API composition while retaining its unprivileged `greiapanel` account and strict Parent-service sandbox.

Parent-installed packages live separately at:

```text
/var/lib/greia-os/activity-packages/active
```

with trust/source:

```text
PARENT_TRUSTED_UNSIGNED
greia-parent-package-service
```

The launcher composes this source through the ordinary registry/runtime/permission/history/supervisor path; it does not copy Parent packages into `/opt` or relabel them as built-in/developer packages.

The pinned external `Greia-Parent-App-Html` revision now:

- asks the API index whether `activities.install` is available;
- only then shows the install form;
- accepts `.greiaactivity` files;
- sends raw authenticated package bytes with `application/vnd.greia.activity+zip` rather than base64/JSON expansion;
- applies the 32 MiB request bound client-side for feedback;
- surfaces typed server rejection messages;
- refreshes Activity inventory on success.

The Greia runtime pin/integrity manifest includes the exact Parent client revision and changed-file hashes. Runtime web fetching is not introduced.

---

# 6. Current tests added but not executed in this connector session

Important new regression source includes:

```text
tests/test_installation_hardware_regressions.py
tests/test_ui_motion_scroll.py
tests/test_launcher_presentation.py
tests/test_activity_packages.py
tests/test_activity_contract.py
tests/test_parent_api.py
```

External Parent HTML source also updates:

```text
tests/api.test.js
```

Do not claim these PASS until they run on an owner-controlled checkout.

---

# 7. Next exact verification step

The focused source suites and `make verify` passed on the 2026-08-18
local-agent checkout (114 focused + 663 aggregate). The next required work is
generated-image and physical acceptance:

1. build a fresh legacy installer/target through the canonical builder;
2. inspect the produced initramfs and confirm the target kernel contains the needed x86 storage modules on the legacy profile;
3. verify media UUID/payload coherence;
4. repeat physical install/boot/input acceptance on the Acer;
5. confirm the installer completion screen shows the simple `greia` / `greia`
   login and no random recovery code;
6. after first boot, confirm the developer target is reachable over SSH as
   `greia` / `greia`, that root SSH login is rejected, and that reboot
   preserves reachability;
7. connect the Parent HTML client and exercise the main Parent password change
   (using a second SSH connection to prove any shared-credential synchronization
   before closing the first) plus child password set/replace/clear;
8. visually inspect the launcher at 1024×600, specifically Activity-name legibility, category icon/header/back layout, scroll behavior, hover/launch effects and focus;
9. exercise an owner-enabled `.greiaactivity` new-install through the Parent HTML client and confirm the running launcher discovers it only after authority rebuild;
10. where available, repeat basic install/launcher acceptance on additional x86 hardware so the Acer does not become a hidden model-specific contract.

Do not convert source structure into a hardware certification claim.

---

# 8. Remaining architecture/product blockers

- **R7 remains open.** Xorg/xinit is still provisional compatibility implementation.
- Generated live/target images must be rebuilt and physically accepted after this reconciliation.
- Parent pairing/encrypted transport remains provisional/open.
- General release `activities.install` stays disabled until transport/security and R10 lifecycle policy justify enablement.
- R10 update/remove/rollback/signature/revocation/save-migration semantics are still open.
- A future non-local/distributed package store would need transaction serialization appropriate to that store rather than local `flock`.
- Category display/localization should become platform-owned vocabulary rather than humanized IDs indefinitely.
- Controller/touch/category interaction, local Back mapping and richer launcher effects need physical acceptance at the Acer floor.
- Activity-name and category-header typography must be revisited when the selected Nunito Sans font is actually integrated; current source still uses the existing font loader.
- R8/R9/R11/R12/R13/R13B/R14 obligations remain governed by the active remediation plan.

---

# 9. Key commits from the final review correction loop

```text
39d3c46b345e6a5b412fb84b89712e1e6060792  launcher: explicit Activity names + category hierarchy
48f15ae95349243023fb8798745eac4a70c184ca  launcher: stable semantic category icons
43687167fc7b51720499ba59cfef6783d1a2b35c  platform: bounded package icon validation
33dbe71a4982723e8659f6546bb91deab78b0dcc  build: remove password SSH bootstrap from base images
eeca76c0b87e617785d4b53bae7b0bd337031091  build: remove password SSH bootstrap from live installer
8ad1153df01b108a7f15eef4f533a54aa8d0677c  tests: forbid password bootstrap in canonical builders
40eca5312577eb7d08e8ca485938d6c45984c370  packages: process-wide install serialization
7fe0a3a41926a271e47598be4bbc92044b37a8ae  tests: prove package lock spans service instances
d392cfb2065eb123b5bc1c1555e364c7d5fd89f8  docs: process-wide Activity install lock
7bb7119c69881910bca430a2a7ec403da5c0456d  review: process-wide package install serialization
```

Commits from the 2026-08-18 local-agent credential/SSH reconciliation:

```text
9676fff  packages: fix archive mode detection, activation cleanup, and already-installed errors
9baa48b  parent: add typed main Parent credential and remove end-install random code UX
c02f838  remote: keep developer installs reachable via greia/greia login
ed3ea70  parent: pin updated Parent App with password change + served client parity
36e2cd9  parent: pin Parent App with per-child password management
9e6f0eb  build: persist appliance-session Xwrapper to the live installer overlay
```

External Parent HTML commits:

```text
32c22d8  parent-ui: add main Parent password change control via typed API
e30bcbc  parent-ui: add per-child password set/replace/clear from the children view
```

Earlier commits in the same tranche contain the Xorg/runtime/input reconciliation, target-kernel-aware initramfs hooks, Parent package API/client, trust-source composition and launcher presentation foundation. Repository history is authoritative for their exact ordering.

---

# 10. Continuation rule

Before further implementation, read in order:

```text
AGENTS.md
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
relevant accepted ADRs
docs/adr/0018-lightweight-ui-foundation.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
docs/agents/GREIA_AGENT_OPERATIONS.md
skills/greia-activity-authoring/SKILL.md
```

Then resume from the first incomplete blocking phase. Do not use the 2026-08-18 package/UI tranche as justification to skip R7 or to label R10 complete.

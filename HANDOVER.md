# Greia — Standalone Engineering Handover

**Date:** 2026-08-18  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Latest reviewed implementation baseline before this handover update:** `224bc38f643129784915d0ede3f49ada9bc126db`  
**Review baseline:** `a66a8ff022fdd77019752847dc0eec02fd3733d0`  
**External Parent HTML revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@6ee02840e2fdfdbe68a6fa5869a8f085b50ae37f`

## Branch and execution policy

`main` is the owner-required development/integration branch. Do not create feature/recovery/work branches unless the owner explicitly changes that policy. GitHub is canonical source persistence.

Do **not** use, query, trigger, rerun, inspect or download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution. Source verification runs on an owner-controlled environment.

## Evidence boundary — do not overclaim

The latest genuinely executed complete owner-controlled aggregate source gate recorded in repository history remains the 2026-08-16 Ubuntu run after the Activity-bytecode validation fix:

```text
focused hardware-enablement suite 1: 77 PASS
focused hardware-enablement suite 2: 32 PASS
full source suite / make verify: 530 PASS
project validation: PASS (4 Activities)
source/shell/footprint gate: PASS
aggregate gate exit: 0
```

Everything in the 2026-08-18 review/implementation tranche below was performed through the connected GitHub repository. **The new Python/Node tests were not executed here. No fresh installer image was built here. No new physical-hardware boot/install PASS is claimed. No GitHub Actions execution was used.**

Physical hardware work performed before this review is valuable evidence of the failures/root causes that motivated the fixes, but the reconciled source now needs a fresh owner-controlled source gate, generated-image inspection and physical acceptance.

## 2026-08-18 — real-hardware installation reconciliation

The most important discovery of this review was that several fixes documented after the Acer hardware debugging were **not all persisted in authoritative build inputs**. A clean rebuild could therefore reproduce failures already solved manually. The review reconciled the build tree with the hardware-proven behavior and added hardware-independent regression locks.

Canonical review:

```text
docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md
```

Reconciled issue log:

```text
docs/INSTALLATION_ISSUES_LOG.md
```

### Installation lessons that are now platform invariants

1. **Build-host hardware is not target-hardware authority.** A VM/chroot cannot decide whether the target initramfs needs a boot-critical controller driver.
2. **Live-media identity and payload are one artifact.** `.disk/live-uuid`, live squashfs/kernel/initrd, installation payload, payload digest and target profile must not drift independently.
3. **A graphical VT is not interactive stdin.** GUI services use `StandardInput=null`; installer subprocesses use `stdin=DEVNULL` unless explicit input is required.
4. **Systemd namespace paths must exist before namespace construction.** Service-owned `/run` paths use `RuntimeDirectory=` rather than an `ExecStartPre` mkdir that is already too late.
5. **Display-service hardening follows the actual backend contract.** The current Xorg compatibility backend cannot be wrapped in desktop-daemon mount namespaces that block its VT/DRM/input/runtime needs.
6. **Xorg console heuristics do not describe Greia's systemd appliance session.** Current provisional wrapper policy is explicit and platform-owned.
7. **Legacy `/dev/input/mouse*` nodes are compatibility aliases, not extra modern pointer devices.** The Xorg compatibility path ignores them and consumes event devices.
8. **Bubblewrap mount destinations must be constructed inside the private filesystem before binds.** `/run` is private tmpfs; required bind targets are explicit; the previously broken user-namespace assumptions remain removed.
9. **A kiosk without a window manager still needs explicit keyboard-focus handoff.** The current X11 compatibility path uses `XSetInputFocus`.
10. **Developer access fails closed.** Normal/release remote access stays off; developer access is key-only and root/password SSH remains disabled.
11. **A hardware fix is not complete until the machine works, the build input contains the fix, a hardware-independent regression protects the cause, and documentation explains the failure class.**

### Boot/initramfs hardening

Both installed-target and live-installer image inputs now include:

```text
MODULES=most
ahci
libata
sd_mod
```

and executable initramfs hooks:

```text
build/overlay/etc/initramfs-tools/hooks/greia-storage-modules
build/installer-overlay/etc/initramfs-tools/hooks/greia-storage-modules
```

that explicitly call `manual_add_modules` for the generic SATA/AHCI root-storage stack. This is intentionally redundant defense against build-host probing omissions.

`tests/test_installation_hardware_regressions.py` locks the source-level hardware-independent invariants.

### Launcher/Xorg service reconciliation

Authoritative build inputs now preserve the hardware-proven provisional Xorg behavior:

- `RuntimeDirectory=greia-os` / mode `0755`;
- `StandardInput=null`;
- current Xorg-incompatible `ProtectSystem`, `ProtectHome`, `PrivateTmp` and restrictive `ReadWritePaths` removed from the Xorg-owning launcher service;
- `Xwrapper.config` uses `allowed_users=anybody` and `needs_root_rights=yes` for the platform-owned appliance session;
- `/dev/input/mouse*` compatibility nodes are ignored before libinput pointer/touchpad matching.

This is **not** a decision to retain Xorg permanently. R7 remains open and the current service configuration is the known-good compatibility contract until the selected direct/session backend is proven on hardware.

### SSH security-floor correction

The review found stale developer-builder convenience branches that still write a historical `greia/greia` password and permissive SSH settings. Those branches conflict with the current key-only developer architecture.

The generated target and live-installer overlays now include an earlier `00-greia-security-floor.conf` that requires public-key authentication, disables password/keyboard-interactive authentication, disables root login and denies historical `root`/`greia` remote identities. First boot also locks historical root/greia passwords.

**Remaining cleanup:** delete the obsolete password-writing branches from the large builders themselves after a controlled builder-focused test. The security floor makes them non-authoritative now, but dead insecure code should not remain indefinitely.

## 2026-08-18 — lightweight launcher interaction foundation

Canonical design:

```text
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

The launcher lifecycle/security core remains `LauncherApplication`. Richer child-facing presentation is now composed in `GreiaLauncherPresentation`; this avoids turning profile/session/package/runtime authority into UI code.

New reusable layers:

```text
src/greia_platform/ui_motion.py
src/greia_platform/ui_scroll.py
src/greia_platform/pygame_effects.py
src/greia_platform/activity_assets.py
src/greia_launcher/catalogue_view.py
src/greia_launcher/presentation.py
```

### Implemented launcher behavior

- shallow cached card/icon shadows;
- bounded hover/selection lift and scale;
- stronger focus outline;
- short ~420 ms squiggle/bounce launch flourish before the existing starting overlay/authoritative launch path;
- two-row visible Activity window rather than unbounded widget creation;
- responsive two/three-column layout;
- keyboard selection keeps the selected Activity visible;
- mouse-wheel semantic-row scrolling;
- explicit scroll controls only when needed;
- category tabs/pills;
- bounded icon/font/shadow/decorated-icon caches;
- installed X session now starts `python3 -m greia_launcher.presentation`.

The effects are deliberately cheap sampled transforms and cached surfaces, not a scene graph/compositor/general animation framework. They must remain suitable for the 1024×600/i686 resource floor.

## Activity navigation categories are now distinct from education tags

The previous `education.categories` values describe learning/skill taxonomy and are not an appropriate permanent launcher information architecture. The manifest now optionally carries:

```toml
[presentation]
categories = ["create", "learn"]
```

while preserving:

```toml
[education]
categories = ["creativity", "geometry", "fine_motor"]
```

New launcher categories are bounded and distinct from progression metadata. API-0.1 packages with no `[presentation]` table retain an explicit compatibility fallback to educational categories.

Current first-party launcher grouping:

```text
All
Create        -> Painting, Shape Garden, Writing
Learn         -> Shape Garden, Writing
My Greia      -> Workshop Settings
```

The category ordering model also understands `Play` and `Explore` for future Activities.

## Activity-owned icons

Existing built-ins remain valid with catalogue IDs such as:

```toml
icon = "palette"
```

Portable packages can now declare a package-owned icon:

```toml
icon = "package:assets/icon.png"
```

The platform-owned `activity_assets` validator requires a contained relative PNG/WebP path with bounded depth/length. Parent package installation validates the icon before activation; the launcher does not use arbitrary host paths as presentation assets.

## 2026-08-18 — guarded `.greiaactivity` new-install foundation

This tranche implements a real **new-install** seam, but it does **not** close R10.

New platform service:

```text
src/greia_platform/activity_packages.py
```

It accepts a bounded ZIP-based `.greiaactivity` whose `activity.toml` is at archive root and performs:

1. request/archive size and entry-count bounds;
2. traversal/absolute/backslash/hidden/portable-duplicate path rejection;
3. encryption/symlink/special-file/compression-bomb rejection;
4. streamed private staging;
5. ordinary `ActivityRegistry` validation against built-ins + installed Parent packages;
6. package-owned icon validation;
7. `PARENT_TRUSTED_UNSIGNED` provenance;
8. digest-addressed read-only immutable version storage;
9. prepared read-only active tree;
10. audit receipt preparation;
11. atomic active-directory rename as the install commit point.

Existing Activity IDs are rejected. Updates, removal, rollback selection, signatures/revocation, curated-store policy and transactional save migration are still open R10 work.

### Adversarial corrections made during this review

Two cross-component problems were found after the first implementation and fixed before handover:

- `/var/lib/greia-os` was previously `0750`, so `greiakid` could be unable to traverse to the Parent-installed read-only Activity source. It is now traversal-only `0755`; sensitive descendants retain their own private modes. `StateDirectoryMode=0755` migrates an existing Parent state root.
- a hot-installed Activity could initially have appeared in the catalogue without rebuilding runtime/permission/history/supervisor authority. `GreiaLauncherPresentation` now validates the new registry set and rebuilds runtime services/supervisor **before** publishing the new catalogue; failure preserves the last known-good pair.

The install transaction was also tightened so a receipt-write failure cannot return an API failure after executable code has already become visible. Interrupted immutable versions are digest-verified before retry reuse.

## Parent API / HTML Activity installation

Greia now defines:

```text
POST /api/v1/activities/install
```

but the ordinary protocol capability remains:

```text
activities.install = false
```

`greia_parent.package_api` advertises it only when explicitly owner-enabled or on a developer image marker. This is deliberate because the current Parent transport is still provisional plaintext HTTP. **Release images do not gain executable package upload merely because the typed package service exists.**

`greia-parent.service` now starts the package-aware API composition while retaining its unprivileged `greiapanel` account and strict Parent-service sandbox.

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

The external `Greia-Parent-App-Html` client revision pinned by the OS now:

- asks the API index whether `activities.install` is available;
- only then injects the install form into Activities;
- accepts `.greiaactivity` files;
- sends raw authenticated package bytes with `application/vnd.greia.activity+zip` rather than base64/JSON expansion;
- applies the 32 MiB request bound client-side for feedback;
- surfaces typed server rejection messages;
- refreshes Activity inventory on success.

The Greia runtime pin/integrity manifest includes the exact changed Parent client files and hashes, so release images still use integrity-checked build input rather than runtime web fetches.

## Current tests added but not executed in this connector session

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

## Next exact verification step

On an owner-controlled current Linux checkout, preserve the first failure and run focused source verification before the aggregate gate. At minimum include:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_installation_hardware_regressions \
  tests.test_ui_motion_scroll \
  tests.test_launcher_presentation \
  tests.test_activity_packages \
  tests.test_activity_contract \
  tests.test_parent_api -v

make verify
```

In the external Parent HTML checkout at the exact pinned revision, run its normal Node test command from `package.json`.

If source gates pass, rebuild the legacy installer/target through the canonical builder and inspect the generated artifacts, including the produced initramfs module content. Then repeat physical install/boot/input/Activity-launch acceptance on the Acer and, where available, additional hardware. Do not convert source structure into a hardware certification claim.

## Remaining architecture/product blockers

- **R7 remains open.** Xorg/xinit is still provisional compatibility implementation.
- Generated live/target images must be rebuilt and physically accepted after this reconciliation.
- The stale password-writing builder branches are neutralized but should be deleted under a controlled builder test.
- Parent pairing/encrypted transport remains provisional/open.
- General release `activities.install` stays disabled until transport/security and R10 lifecycle policy justify enablement.
- R10 update/remove/rollback/signature/revocation/save-migration semantics are still open.
- Category display/localization should become platform-owned vocabulary rather than humanized IDs indefinitely.
- Controller/touch/category interaction and the richer launcher effects need physical acceptance at the Acer floor.
- R8/R9/R11/R12/R13/R13B/R14 obligations remain governed by the active remediation plan.

## Continuation rule

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

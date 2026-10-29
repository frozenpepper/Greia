---
name: greia-os-work
description: Task router for substantive Greia OS/platform/Shell/Parent/installer/simulator/build/runtime/hardware-service work. Load only the task-specific local docs required for the work.
---

# Greia OS Work — task router

**Status:** LIVING derived contributor router  
**Reviewed:** 2026-09-21

This file tells an agent **what to read for the task**. It is deliberately not a second architecture manual.

## Current voice screening and direction correction (2026-10-21)

Screening policy v2 requires ASR >0.8; tail/internal pauses below 1.5s do not warn.
Reassess matching saved reports without another model run; see automated review
procedure §3a. Master design owns identity/register/timbre; per-cue prompts own
only performance. Defaults are neutral for all six characters. Do not revive
v2's persona-prefixed frozen overrides for the next Dani/Momo/Tito replacement.

## Shared human listening tool (2026-10-21)

After automated review, use shared `takeboard` (catalog/skill/README at
`/Volumes/Test1/Works/takeboard`) for HTML generated/master comparison and
save/export/reload of human state, 1–5 scores and notes. Greia's thin adapter
is `tools/export_voice_review_batch.py`; exact commands are in
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` §6. Keep its manifests external.
Machine findings never initialize human acceptance. Takeboard edits only its
review JSON; importing decisions into Greia receipts/runtime is a separate task.

## Extending Greia's language set

For a new installer/OS/Parent/Activity language, route first to
`skills/greia-language-expansion/SKILL.md` and
`docs/development/ADD_A_GREIA_LANGUAGE.md`. Offered languages are
manifest directories at `src/greia_platform/languages/<locale>/manifest.json`,
not a list to extend in Python. The helper tools scaffold and check per-locale
JSON/TOML without enabling an unfinished language. Build/device and native
speech acceptance are still separate. Do not change `main` merely to make a
staged language appear release-ready.

## Universal rules

1. Work from current `main`; preserve concurrent changes. Read `AGENTS.md` and `HANDOVER.md` first.
2. Accepted ADRs own architecture; source/runtime declarations own exact implemented APIs/schemas/limits; product docs own accepted child-facing behavior.
3. Greia Shell is the child-facing OS surface. Do not expose a generic Linux desktop/shell/package-management path during normal child use.
4. Platform authority stays platform-owned: profiles/sessions, trust/packages, permissions, Home/Back, physical input, system controls, microphone routing/processing, storage/history, progression/rewards, install/update authority and hardware facts.
5. Low-resource behavior is correctness. The Acer reference floor is not a later optimization target.
6. GitHub-hosted Actions/execution are opt-in only and require explicit owner authorization.
7. Claim only evidence that actually ran. Source, authoring-provider+human, browser, Simulator, VM/image and physical evidence are distinct.
8. After substantive implementation, update the active plan/HANDOVER and affected living manuals/skills as required by `AGENTS.md`. Refresh affected ignored `.agents/skills/` copies from canonical `skills/` when this workstation uses installed copies.
9. New prerecorded Greia speech is authoring-time work through `tools/greia_voice.py`; OS/Activity/shared-library code must not grow a parallel TTS/ASR backend.
10. Launcher spoken labels are Shell-owned prerecorded assets; no child-runtime TTS and no Activity-owned hover/focus speech.
11. Display/session/input abstraction must preserve direct safe Activity SDL/Pygame rendering and high-rate input paths; do not introduce avoidable full-frame copies or generic high-rate IPC merely for abstraction symmetry.
12. Repository verification must not traverse arbitrary git-ignored build/evidence/cache state. Privileged release attempts may legitimately leave root-owned preserved evidence under ignored paths; source cleanup/footprint gates must stay scoped to source-owned/tracked material rather than requiring deletion/chown of retained evidence.
13. Privileged release/build orchestration must not write generated Python bytecode into the developer-owned checkout. Owner release execution and its subprocess tree must run with bytecode writing disabled. Source-bytecode cleanup has one explicit source-scoped owner and must fail closed on traversal/deletion errors rather than using brittle Make/shell-variable loops or returning a false-green verification result.

Before installing/configuring anything also read:

```text
SETUP.md
docs/agents/GREIA_AGENT_OPERATIONS.md
```

For current evidence/test routing use:

```text
docs/testing/LOCAL_AGENT_START_HERE.md
```

## Hardware firmware resolution and service sandboxes

Driver firmware for the installed target is found with `modinfo` (directly and through isenkram), so any service that resolves it (`greia-install-transaction`, `greia-system-update`) must keep `/usr/lib/modules` readable: never add `ProtectKernelModules=yes` there; deny module loading with the capability bounding set and `SystemCallFilter=~@module` (pinned by `tests/test_firmware_resolution_unit_contract.py`). Production compositions pass `LinuxKernelModules` to the resolvers so unreadable metadata is an incomplete plan (pre-erase refusal), never "no firmware needed". Fixture tests with fake `modinfo` cannot prove this; check a hardening change in a real `systemd-run` sandbox.

## Pi 400/500 source-only adapter (owner-authorized, 2026-10-19)

For Pi A/B release work, read `docs/reviews/2026-10-19_RASPBERRY_PI_RESEARCH_LED_VERIFICATION.md` before changing the firmware path. The `greia_platform.pi_boot_observation` module is read-only and **not** a boot-health verifier or production boot transaction: big-endian chosen-firmware values and a root= hint cannot establish the actual mounted root or boot-device ancestry. Pi kernel, DTB, EEPROM partition walk and FAT A/B success all need real-board proof. Preserve the no-erase Pi installer gate.

## Pi 400/500 source-only adapter (owner-authorized, 2026-10-19)\n\nPi support is **not implemented as a bootable installer**. Experimental ARM64 profiles and native Pi A/B partition and boot-asset source now exist. The full installer deliberately refuses Pi before erasure, and the Phase 0 image composer refuses ARM64. For hard findings, precise tests and remaining required boot/update/hardware work, consult `docs/reviews/2026-10-19_RASPBERRY_PI_INSTALLER_SOURCE_REVIEW.md` and the authoritative 2026-09-15 lifecycle plan. Validate the **committed file**, not merely staged Git blobs or a review claim. No hosted Actions runs without owner opt-in.\n\n## Physical installer boot: live-root service identities (2026-10-29)

When reviewing the legacy-x86 USB installer, check the actual *live installer*
`/etc/group` against `greia-installer.service`
`SupplementaryGroups=` before claiming boot acceptance. The first physical
Acer 2026-10-28 candidate failed at `216/GROUP`: target-role `netdev`
provisioning did not apply to the live root, so the GUI never started.
The shared composer now creates the live groups and the composed-root verifier
rejects any missing identity. Route acceptance through
`docs/reviews/2026-10-29_ACER_USB_INSTALLER_216_GROUP.md`. QEMU transaction-
socket acceptance alone does **not** prove the systemd UI launches. Retest the
actual default service in QEMU and on hardware after a corrected image rebuild.

The next physical Acer install failed inside the `initramfs-tools` postinst
with `zstd ... No space left on device`: the 1,664 MiB SYSTEM_A slot held the
payload and hardware-support packages, while `mkinitramfs` needed an ~182 MiB
temporary tree plus a 42 MiB initrd. Keep transient apt/initramfs bytes out
of SYSTEM_A: the installer mounts a bounded 256 MiB tmpfs at
`/run/greia-installer-scratch` and directs `TMPDIR` and
`Dir::Cache::archives` there. Do not relax capacity checks or enlarge
boot-control/PERSIST to hide this. Route to
`docs/reviews/2026-10-29_ACER_USB_INSTALL_ENOSPC_INITRAMFS.md`.

## Current blocking route: post-R1 product-composition closure + multiplatform lifecycle plan

Install/update/release/multiplatform lifecycle work routes to
`docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`
(the ADR 0036 successor plan), not to signed-bundle or Gate-P5/V12G/D6
closure. That plan owns lifecycle sequencing and closure criteria; the
2026-08-08 architecture-remediation plan remains blocking only for its
remaining non-lifecycle obligations.

Session 03 was closed by the Linux owner-command release build on 2026-09-23.
Session 04 remains OPEN: fresh A/B install, first acceptance, alternating
updates and rollback must execute using real current bundles. The current consolidated Linux test route is
`docs/testing/GREIA_UPDATE_RELEASE_ACCEPTANCE.md`. Older dated A/B and
application-package work orders remain detailed reference material, not
additional stop/reuse gates.

The 2026-10-23 Parent delivery, persistent mounts and restart integration are
source work. Do not call them installed/device acceptance before that work
order runs. `legacy-x86-i686` and its RC profile remain single-root and cannot
activate A/B updates; do not advertise a software-only migration.

ADR 0038 separately supports Python, built-in Activity, Parent Activity and
combined `.greia_update` application packages on single-root or A/B images
that contain the bootstrap marker/helper. This updates application code; it
does not convert a single-root disk to A/B or make full-system updates
available there. Read `docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md`
before building or accepting these packages. A legacy image without the
bootstrap has no package-upload capability or manual bootstrap CLI.

Linux execution evidence is in
`docs/reviews/2026-10-24_SOFTWARE_UPDATE_LINUX_ACCEPTANCE_RESULT.md`: the first
RC run passed application update/rollback cases only on a manually repaired
clone. A clean fixed-source rebuild/install remains required. Parent Activity
storage is owned by `greiapanel:greiapanel`; root update transactions must hand
new artifacts back to that owner without granting the child write access.

For disposable Acer A/B acceptance only, use the explicit
`tools/greia_release.py build-acceptance-fixture` command in the work orders.
Its output is experimental and rejected by the public update-index builder.
The ordinary release build still requires an accepted release-safe boot cover. `greia-early-framebuffer-v1` is registered after the 2026-10-28 QEMU visual acceptance; physical Acer visual acceptance remains outstanding.
Do not treat fixture build/boot success as release eligibility.

The old signed `.greiaupdate` v2 flow and release signing keys are
superseded by ADR 0036 and are not the normal production route; older
references to them are historical only.

**2026-10-27 owner-authorized update implementation/acceptance:** use the
single current [update release acceptance guide](../../docs/testing/GREIA_UPDATE_RELEASE_ACCEPTANCE.md).
The former 1275-era single-stage source gate is historical, not an active
constraint. Its diagnostic already captured a real `sda2` capacity-observation
refusal ([result](../../docs/reviews/2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md),
[analysis](../../docs/reviews/2026-10-27_AB_OLD_RELEASE_STAGE_REFUSAL_ANALYSIS.md)).
Implement a portable block-capacity observation with i386 coverage in current
`main`, then run consolidated current-source A/B and lightweight package tests
on disposable Linux/QEMU installations. One work session may fix, retry and
proceed through the complete relevant matrix; do not stop after every ordinary
failure or require new frozen-source approvals. Do not weaken disk identity,
bounded writes, startup health, recovery, PERSIST protection or child-session
safety. Language JSON delivery has source-level tests; installed acceptance on fresh
current images remains to do. The pre-release legacy receiver bridge was
removed: no old-development-image upgrade/migration acceptance is required.

The installed updater discovers the fixed published bundle directly. Status
is reporting/recovery progress, not a package-admission requirement. Device
jobs, slot journals and recovery remain. Routine Python/Activity updates use
small `.greia_update` packages without rebuilding OS images for each update.
Session 04 remains OPEN until the Linux lifecycle predicates actually pass.

Session 04 owns the real legacy-i386 fresh-install/update/rollback lifecycle. The
`POSTR1-P1-INSTALLER-RED` / Gate-P5/V12G/D6 routing below is historical and
superseded for lifecycle sequencing. Source composition primitives (T3-S) are
done; exact shipped installer/update/boot-health product composition (T3-P)
remains OPEN/BLOCKING until closed through the 2026-09-15 plan. T7 remains
valid only in its disposable/device-harness scope. See `HANDOVER.md` §2/§8
and the active lifecycle plan for current disposition.

Do not start Raspberry Pi 400/500 work, UEFI work, destructive Acer
installation, or backup work in this lane, and do not treat shipped
product composition as complete. Pi/UEFI adapters resume only after the
common product lifecycle is proven.

## Creations Library / first-party Activity release workstream

For child-created PNG/WAV/UTF-8 sharing, the universal pre-reader picker/viewer, shared adaptive storage capacity guard, Painting/Shape Garden/Theatre/voice/text interoperability, and the 45-built-in quality/release audit, read:

```text
docs/product/CHILD_CREATIONS_LIBRARY_AND_MEDIA_INTEROPERABILITY.md
docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md
docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PROGRESS.md
src/greia_platform/creation_capacity.py
src/greia_platform/creation_media.py
src/greia_platform/creations.py
```

P1 remains the trusted repository; P2 provides the manifest-bound **publish-own-private-file/import-child-selected-handle** seam over the existing per-session socket. P3 SOURCE-WIP includes the common gallery/picker renderer, audio preview owner, authenticated nonblocking request/poll/cancel coordinator, and **trusted modal presentation**: Legacy-X keeps native window handles private, re-proves the foreground window's `_NET_WM_PID` against the supervised process before raising Greia's existing Shell window, and restores the Activity afterward; Simulator diverts its existing remote display/input transport to the same Shell picker and prevents Activity frame overwrite while the modal is active. Painting is the first real PNG producer+consumer and exposes child-visible up-arrow publish / down-arrow import actions; import polls at a bounded cadence and saves an independent private editable copy. **All of this latest modal/import work is untested in a complete checkout/GUI**, so do not call P3 accepted yet. Do not mount a shared folder, duplicate choosers per app or expose arbitrary library listing/deletion to an Activity. Follow `P3_TRUSTED_PICKER_DISPLAY_CONTRACT.md` and the consolidated deferred acceptance before promotion. Wayland/KMSDRM still require their own backend implementation of the same runtime-neutral modal lease.

## Broad architecture / new platform seam

Read:

```text
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/adr/0012-platform-architecture-constitution.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

Use this broad set only when the change genuinely crosses subsystem boundaries.

## Boot, GRUB, Syslinux, initramfs, first boot, X startup, recovery

Read **first**:

```text
skills/greia-os-work/BOOT.md
```

Then as relevant:

```text
docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/design/GREIA_BOOT_EXPERIENCE.md
docs/design/GREIA_BOOT_PROGRESS.md
```

Do not modify physical boot/recovery state from memory.

Live installer recovery source (2026-10-17): live entries require
`nonetworking` (disables live-boot ifupdown setup, not userspace iwd/networkd).
`greia-installer.service` owns bounded `Restart=always` retries and invokes
`installer-exit-cover` after stopping; xinit's successful exit cannot be used
to infer that the installer client succeeded. Exact limits and paths belong
to the unit/helper and `build/lib/verify-composed-root.sh`. Rebuilt-image and
physical quiet-screen/recovery evidence remain separate from source tests.

Quiet media presentation (owner decision 2026-10-18): the quiet Syslinux
template clears the stock version/copyright banner with the one-byte
`build/live-syslinux/clear.msg` (`DISPLAY /boot/syslinux/clear.msg`); the writer
places the byte on quiet media only and the read-only verifier requires and
byte-compares it, refusing any `DISPLAY` on the diagnostic/recovery template.
`console=tty1` + `panic=0` stay (a panic still prints), and the hidden
`verbose` label remains the recovery path. This separated the clear file from
the fatal `console=null` rollback of 2026-08-20. See
`docs/INSTALLATION_ISSUES_LOG.md` §34–§35.

Installer completion power-off (2026-10-18): the unprivileged UI writes
`/run/greia-installer/finish-request`; the root
`greia-installer-finish.path` watches it and `greia-installer-finish.service`
performs the single power-off after lowering PID1's `LogLevel` to `emerg`, so
`systemd-shutdown` teardown text never draws over the Greia cover. The UI must
not call `systemctl poweroff` directly (logind/polkit denies `nobody`). The
composed-root verifier enforces the units, helper and silence. See
`docs/INSTALLATION_ISSUES_LOG.md` §36.

## Installer, image composition or build pipeline

Read:

```text
docs/adr/0013-declarative-image-profiles-and-composable-build-artifacts.md
docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md
docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md
SETUP.md
```

Inspect current builders under `build/` before changing generated target state. Boot-impacting changes also require `skills/greia-os-work/BOOT.md`.

Partition-scanned loop ownership is centralized in
`build/lib/safe-cleanup.sh`. Any build/tool path that creates a
`losetup --find --show --partscan` loop must use `safe_detach_loop`; do not
directly call `losetup -d` and then clear the loop variable. Linux detach is
lazy and open partitions count as disk openers. The required order is:
unmount -> request parent detach -> settle -> if still bound with partition
children, bounded `partx -d` as a **post-detach fallback** -> settle -> verify
both backing association and children are gone -> clear/delete. Cleanup pins
backing identity against loop-number reuse, emits opener/holder diagnostics on
failure, and cleanup failure must become process failure rather than merely
being logged from an EXIT trap.

## Shell, launcher, Collections or lightweight UI

Read:

```text
docs/adr/0018-lightweight-ui-foundation.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Inspect:

```text
src/greia_launcher/
src/greia_platform/ui_*.py
```

Collections provide semantic data; do not create category-specific copies of common Shell behavior.

Interactive Home (2026-10-16): `home_animator.HomeAnimator` is the single owner of Home ambient motion (greeter reactions/blink/sleep, ≤3 falling apples, sun sparkles, two drifting clouds; ≤6 live effects, sprites pre-scaled once per layout). `home_animation_presentation.HomeAnimationMixin` draws it as an overlay after the cached Home blit and presents small dirty-rect frames through the Shell loop hooks `_present_ambient_frame` / `_ambient_wait_seconds` (`presentation.py`): ≤24 fps, awake window 20 s after input, then zero redraws (one `sleepy` swap at 60 s). Scenery geometry is `home_scenery.py` (scene-space facts mirrored from `home_landscape.svg`, switched off wherever it would touch a target/HUD). Portals and system chrome always win hit-testing. Other Shell presentation makes the greeter react via `_home_react(kind)` (`surprised`/`happy`/`cheer`/`wave`), never by drawing it. Add new ambient effects inside `HomeAnimator` (bounded, no per-tick surface work), not as new animating sources in the loop. Tests: `tests/test_launcher_home_animator.py`, `HomeAmbientPacingTests` in `tests/test_launcher_pacing_dirty_redraw.py`.

## Protected Activity Home/Back and lifecycle chrome

Read:

```text
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/archive/reviews/2026-08-29_R7_R73_ACTIVITY_CHROME_MIGRATION_TRANCHE.md
docs/archive/reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md
src/greia_launcher/system_chrome.py
src/greia_launcher/system_chrome_legacy_x.py
src/greia_launcher/trusted_chrome_supervisor.py
```

Real Home/Back is platform authority. First-party Activities must not restore retired cooperative Home helpers or request Activity-side canvas chrome.

Current strict ownership gate:

```bash
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

The September 2026 missing-Home composition regression is fixed and physically verified at its exact candidate. Current scope/evidence is in `HANDOVER.md`.

## R7 display/session/backend work

Read:

```text
docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
src/greia_launcher/display_session.py
src/greia_launcher/display_session_legacy_x.py
src/greia_launcher/system_chrome.py
src/greia_launcher/system_chrome_legacy_x.py
src/greia_launcher/trusted_chrome_supervisor.py
src/greia_launcher/trusted_presentation.py
src/greia_platform/activity_backend_policy.py
```

Preserve these seams:

- `DisplaySessionCoordinator` owns Shell/Activity surface lifecycle;
- concrete display backends own transport mechanics;
- `SystemChromeCoordinator` owns Home/Back semantic authority;
- `TrustedChromeActivitySupervisor` binds chrome to Activity stop/cleanup authority;
- installed primary and fallback Shell paths both preserve trusted chrome;
- Activity source stays backend-neutral;
- shared X11 is migration plumbing, not final malicious-client isolation.

Current audits:

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

Do not begin a new R7 subphase by relying on stale physical evidence from an older runtime candidate; follow `HANDOVER.md`.

## Input, controller, pointer or touch ownership

Read:

```text
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/testing/2026-08-15_PHASE0_INPUT_CONTROLLER_ACCEPTANCE.md
```

Physical device/controller details stay below runtime-neutral semantics. Ordinary Activities do not receive raw `/dev/input` to implement convenience mappings.

## Network / Wi-Fi ownership

Read:

```text
docs/INSTALLATION_ISSUES_LOG.md            (§13 wireless link ownership)
src/greia_platform/wifi.py                 (iwd backend: available/scan/connect)
build/installer-overlay/etc/iwd/main.conf  (live-installer L3 owner)
build/overlay/etc/iwd/main.conf            (installed-target L3 owner)
build/*/etc/systemd/network/               (role-specific networkd policy)
build/lib/compose.sh                       (compose_configure_systemd enable lists)
```

**Association/authentication and IP configuration are separate ownership
questions.** Greia ships no `wpa_supplicant`, so `iwd` is the sole Wi-Fi
station/authentication authority in every role. L3/DHCP ownership is
role-specific and must be checked together with `iwd/main.conf`:

- **Live installer:** `EnableNetworkConfiguration=true`. iwd owns both
  association/authentication and IP configuration. Its wireless
  `.network` file must therefore use `[Link] Unmanaged=yes`; networkd must
  not run a second DHCP client on the same wireless link.
- **Installed target:** `EnableNetworkConfiguration=false`. iwd owns
  association/authentication only, while systemd-networkd owns L3/DHCP. Its
  wireless `.network` file must therefore retain `[Network] DHCP=yes` and
  must not mark the link unmanaged.
- Never generalize one role's L3 policy to the other. The paired config files
  are the authority; tests and artifact verifiers must reject both bad states:
  two DHCP owners and no DHCP owner.

Other hardware-proven traps remain:

- **Do not probe iwd as `su nobody`.** iwd's bus policy allows `root` and
  group `netdev`. `su` does not inherit systemd `SupplementaryGroups`, so
  a `su` probe returns `Access denied` even when the real service reaches
  the bus fine. Probe with
  `setpriv --groups=$(getent group netdev | cut -d: -f3)`, or trust the
  installer's own report.
- **The installer persists iwd `.psk`/`.open` profiles into the target**
  (`engine.py` → `request.wifi_profile.write_to`). The installed target must
  keep iwd in station/authentication authority while networkd supplies DHCP.
- **iwd owns `/var/lib/iwd`. Never write into it from an unprivileged
  process.** It is `root:root 0700`; the installer is `User=nobody`, so any
  attempt fails with `[Errno 1] Operation not permitted`. To hand iwd a
  passphrase, register a `net.connman.iwd.Agent` and answer
  `RequestPassphrase(object network) -> string`; iwd persists the profile
  itself.
- **Two iwd-agent traps, both found only on real hardware.** The image's
  python3-dbus rejects the three-argument `dbus.Interface(bus, path, iface)`
  form with `TypeError` — use `bus.get_object(...)` then
  `dbus.Interface(proxy, iface)`, the shape the rest of `wifi.py` already
  uses. And `dbus.SystemBus()` is a shared singleton the scan path already
  opened with **no main loop**, so exporting an object on it raises
  "connections must be attached to a main loop"; the agent needs its own
  `BusConnection` with an explicit main loop, and should answer only for the
  selected network's object path.

## Responsive display / viewport / coordinate-space work

Read:

```text
docs/adr/0026-resolution-adaptive-ui-layout.md
docs/adr/0027-activity-coordinate-spaces-canvas-and-world-camera.md
docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md
```

## Display facts, suitability, and pointer/display settings (ADR 0035)

Entry point for physical display facts and suitability policy:

```text
src/greia_platform/display_metrics.py
```

- `DisplayMetrics` holds raw facts only; unknown physical size is explicit, never invented, never assumed 96 DPI.
- `DisplayPolicy.phase0()` decides suitability by envelope comparison; `1024×600` is a preferred default, not a whitelist branch.
- `PhysicalUiPolicy.minimum_pixels` floors shared interactive minimums (8–320 px); it never scales a layout globally.
- `responsive_layout.py` stays geometry-only: no subprocess, no `xrandr`/`xinput`, no model or resolution-equality branches.
- Legacy-X translation lives only in `hal_legacy_x.py` (hardware-session controller, `probe_display`, `probe_pointers`); UI layers never call backend commands.
- `HardwareSettingsStore` (schema v2, tap-OFF) owns desired pointer state; the watcher applies it; installer preview and Parent controls use only the `PointerSettingsController` seam with semantic settings.
- Unknown metrics fail open (full controls, no install block); provably-unsupported modes block destructive install with a clear message.
- No CTM command in any ordinary apply path; no hard-coded device names in generic startup. CTM or model-specific handling requires physical evidence plus architecture review.
- Trusted-action floor (`TRUSTED_ACTION_MINIMUM_MM`, `resolve_trusted_action_minimum_px`) is defined once in `src/greia_launcher/system_chrome.py`; import it, do not duplicate it.
- Activity/catalogue pins follow live catalogue discovery, per the standing owner rule accepting Sottomarino and any new activity.

## Activity runtime, package, permissions, trust or lifecycle

Read:

```text
docs/architecture/GREIA_ACTIVITY_ECOSYSTEM.md
docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md
docs/adr/0017-platform-owned-sessions-events-progression-and-reward-ledger.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0023-open-activity-ecosystem-distribution-and-official-catalogue.md
docs/adr/0033-fail-soft-activity-crossbindings-and-dev-noise-scrub.md
runtime/child-runtime.toml
src/greia_launcher/runtime_adapter.py
src/greia_platform/activities.py
src/greia_platform/activity_packages.py
src/greia_platform/activity_tree_cleanup.py
src/greia_platform/trust.py
src/greia_platform/activity_backend_policy.py
```

For Activity implementation itself, use `skills/greia-activity-authoring/SKILL.md`.

## Supported-language declaration (manifest-based; four currently released)

The **currently offered** OS locales are `en`, `it`, `es`, `fr`
(owner decision 2026-10-17). The single selectable registry is
the set of `src/greia_platform/languages/<locale>/manifest.json`
files, loaded by `src/greia_platform/system_language.py` into
`SUPPORTED_SYSTEM_LANGUAGES` / `SUPPORTED_SYSTEM_LOCALES`. Installer,
on-device Parent panel, Parent API, privileged language helper and simulator
consume that one registry. New ordinary LTR locales add resources, voice and
Activity TOML/JSON without editing Python chooser lists. Stage translations
without a manifest; run
`PYTHONPATH=src python3 tools/check_greia_language.py <locale> --staged`
to validate UI schema and format placeholders (including nested format
fields) before owner-approved promotion. The release contract then
checks manifest-derived text/Activity/audio coverage; device/UI review
remains separate. Follow `docs/development/ADD_A_GREIA_LANGUAGE.md`
and `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`.
Any newly authored Shell/installer/Parent text still requires accurate
translations for every offered locale.
Historical unsupported records are left intact and read as safe
English runtime fallback. Do not install voice/TTS models on Greia OS.
New authoring-time provider adapters belong only under
`tools/greia_voice_core`, with Modal a proposed authoring backend,
not a current runtime feature.

### Installed Parent locale translation seam (2026-10-13)

On-device Parent Settings `ParentSettingsOverlay` renders semantic
password/authentication, eight tabs, title and device language controls
via `src/greia_launcher/panel_localization.py`. This is source-staged
for EN/IT/ES/FR, all four selectable.
**Do not** introduce a second locale store, set Linux `LANG`,
or translate user-entered child names, SSIDs, passwords or service
machine data through an arbitrary substring dictionary.
Use semantic keys with named format fields. When adding dynamic
UI text, ensure `_device_locale` participates in the Parent
overlay's cached composite and pre-rendered chrome keys; reuse
`panel_layout.fit_single_line` or measured wrapping so longer
translated text cannot overflow on the 1024×600/Acer floor.
Follow `tests/test_panel_localization.py`,
`tests/test_panel_frame_cache.py` and `tests/test_parent_panel_polish.py`;
draw panel controls with the overlay's `_kit_button`/`_kit_toggle`
helpers (ADR 0037 look, `_Ink` tokens) and check layout with
`tools/panel_screenshots.py` (1024×600 + 800×480, EN/IT/ES/FR). The implemented Parent forms, audio, pointer, Wi-Fi, SSH and Info
tab copy now also use the same locale resource; service-origin
errors and any custom/inline text not yet extracted are still
coverage items. A failed hardware setting write must never be
followed by an invented success message. The separately maintained
Parent HTML browser client still needs its own localization and
pinned-build review.

## Activity discovery, age guidance or Parent catalogue filtering

Read:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
skills/greia-activity-authoring/DISCOVERY.md
src/greia_platform/activity_discovery.py
src/greia_platform/activities.py
src/greia_launcher/activity_policy_presentation.py
src/greia_launcher/child_shell.py
src/greia_launcher/trusted_presentation.py
src/greia_parent/api_server.py
docs/testing/2026-09-03_ACTIVITY_AGE_POLICY_ACCEPTANCE.md
docs/testing/2026-09-04_CHILD_ACTIVITY_POLICY_FAIL_CLOSED_ACCEPTANCE.md
```

The platform owns the effective catalogue. Do not create a second browser/Activity age engine. Parent Activity visibility/age/difficulty policy is mandatory launcher authority, not an optional adaptive-presentation feature: both the normal rich Shell and the trusted emergency fallback must project it before exposing any Activity. The normal Shell may add adaptive sub-Collections after filtering; the trusted fallback remains direct/non-adaptive rather than bypassing policy.

A genuinely missing discovery-policy file is the legitimate default. A policy path that exists but is malformed, unreadable, an unsupported schema, or a symlink must fail closed to zero launchable Activities until repaired; never coerce invalid policy state to `ActivityDiscoveryPolicy()`/`show_all` as a recovery shortcut. Repair must be detected through the bounded reload/rescan path without a permissive interval.

Adaptive sub-Collection hysteresis is launcher-owned presentation state, not Parent authority. Historical `subdivided_collections` may be consumed once as a compatibility seed, but the child Shell must not write adaptive grouping back into the Parent policy file. Never use a stale read-modify-write of Parent policy to persist presentation state: it can clobber a concurrent `always_hide`, age mode or difficulty update.

Canonical Parent modes are:

```text
show_all
recommended_only   # Age N only: declared range contains N
age_and_easier     # Age N + easier: declared minimum <= N
custom
```

`hide_too_simple` is compatibility input only and normalizes to `age_and_easier`; do not use it for new UI or stored output. Every first-party Activity declares a defensible `recommended_age_min`; `recommended_age_max` remains optional for genuinely open-ended experiences. Age suitability and difficulty are independent, and explicit Parent `always_show` / `always_hide` wins over automatic filtering.

The maintained browser client lives in `frozenpepper/Greia-Parent-App-Html` and is revision/integrity pinned before Greia serves it. Browser source acceptance comes before pin advancement.

## Activity Simulator

Read:

```text
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
docs/archive/reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md
src/greia_simulator/
```

Simulator evidence does not prove production display/session/input/hardware behavior. Do not make Activity code branch on Simulator identity or duplicate platform policy inside the Simulator.

## Parent management / Parent API / pairing

Read:

```text
docs/architecture/GREIA_PARENT_MANAGEMENT.md
docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md
docs/product/PARENT_MANAGEMENT.md
```

For per-child Activity age/catalogue policy also read the dedicated Activity-discovery route above. Inspect the current Parent client pin/integrity manifest before changing either repository. Parent/browser code must not gain generic shell/root authority.

**Parents HTTPS (owner decision 2026-10-23):** installed `greia_parent.production_api` serves self-signed TLS on LAN `:8766` and shares its bounded Parent application/mutation lock with local-only HTTP at `127.0.0.1:8767` for `greia_launcher.parent_credential_client`. `greia_parent.parent_tls` creates the certificate/key in `/var/lib/greia-os/parent-tls/` on-device using `openssl`, included in `build/package-sets/platform-base.txt`; never ship one shared key. `Greia-Parent-App-Html` owns HTTPS discovery and local proxy; Greia pins it through `runtime/parent-app-client.toml`/manifest and synchronized vendor/image files. Ordinary browser certificate warning is an accepted tradeoff; do not add CA/QR/cloud/account ceremony. Source tests and device acceptance: `docs/testing/2026-10-23_PARENT_HTTPS_ACCEPTANCE.md`. Do not accidentally enable Activity installs merely because TLS exists. The current `tools/dev_source_deploy.py` intentionally does **not** deploy installed `/usr/share/greia-parent-app` HTML assets, so using it alone on a pre-HTTPS image advances the runtime pin without the required web bytes and prevents `greia-parent.service` from starting. Do not use that source-only method for Parent HTTPS physical acceptance; build an exact-head image or separately implement/review an atomic full HTML-runtime deploy.

## System output controls (volume / mute / brightness / media keys)

Inspect current exact owners:

```text
src/greia_platform/system_controls.py
src/greia_platform/system_controls_legacy_x.py
src/greia_platform/hardware_session.py
src/greia_platform/hardware_session_legacy_x.py
src/greia_parent/protocol.py
src/greia_parent/update_api.py
```

Persistent desired state is platform-owned. Legacy-X mixer/backlight/media-key mechanics stay below the platform seam. Parent API may mutate only typed desired settings; it must not directly own host mixer/backlight devices or expose arbitrary commands.

Because these files changed after the last physically tested Home candidate, use `HANDOVER.md` before making current physical claims.

## System update mechanism

Application package authority is ADR 0038. Full-system release/slot authority
remains ADR 0036 plus the 2026-09-15 lifecycle plan:

```text
docs/adr/0038-lightweight-application-update-packages.md
docs/adr/0036-unified-system-slot-releases-and-platform-install-media.md
docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md
docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md
docs/testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md
```

Historical context only (signing requirements superseded by ADR 0036; the
signed `.greiaupdate` v2 / release-key workflow is not the normal
production route):

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

Use `tools/greia_software_update.py` for typed Python/Activity/combined
packages and full-system wrappers. Keep Python snapshots within the curated
source/runtime allowlist, including offered locale `manifest.json` / `ui.json`
pairs under `src/greia_platform/languages/<locale>/`. These files are validated
and published with the code in one application generation. For release acceptance, test normal packages on a fresh image composed from
current source with the current receiver. No support for old development images,
pre-manifest reader migrations or legacy bridge packages is required.
See `docs/testing/2026-10-27_LANGUAGE_UPDATE_PACKAGE_ACCEPTANCE.md`
for current-source and installed evidence boundaries, and
`docs/reviews/2026-10-27_UPDATE_RELEASE_ACCEPTANCE_RESULT.md` for the installed
A/B plus application-package result. A/B application updates resolve the
booted slot UUID from the installed layout plus `root=PARTUUID=`; terminal job
publication and candidate cleanup share the job lock. A/B images must enable
`greia-candidate-recovery.timer` so a candidate that boots but never becomes
healthy rolls back after the deadline. Do not ship venvs, wheels, native dependencies,
global assets or the Parent HTML integrity-pin pair. Built-in and Parent
Activity sources retain separate trust. Only `full_system` uses the explicit
restart affordance, and only on an A/B-ready image. Builder/inspect tests do
not prove installed Linux acceptance.

## Localization / language / profile presentation / child letter case

Read:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/adr/0032-profile-presentation-and-grammatical-agreement.md
docs/adr/0034-child-text-letter-case-policy.md
src/greia_platform/localization.py
src/greia_platform/language_presentation.py
src/greia_platform/profile_presentation.py
src/greia_platform/child_text.py
```

Child-facing UI defaults to CAPITAL presentation under ADR 0034. Parent-facing surfaces and child-authored content deliberately bypass that transformation.

The platform `LocalizedResources.audio_cue` normally falls back per key,
matching its existing text/audio bundle contract. For **language-bearing**
speech that must not unexpectedly switch languages, pass
`allow_fallback=False`; it restricts lookup to the selected semantic
locale bundle without assuming any filename or directory naming convention.
Keep required instruction authoring and acceptance per locale; a missing
clip is a release blocker, not a justification for runtime TTS.

## Microphone/audio capture processing

Read:

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
docs/archive/reviews/2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md
skills/greia-activity-authoring/MICROPHONE_RECORDING.md
```

Preserve the platform-owned on-demand route, Parent-owned settings, honest raw fallback and no ordinary Activity hardware bypass.

## Prerecorded voice/speech production

After generation, use `docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` and
`tools/regenerate_voice_corpus.py review` for installed-file signal/receipt and
eligible ASR screening. Reports live externally; generation DONE, automated
coverage and human acceptance are separate. This command neither synthesizes,
changes files nor grants approval, and cannot download models.

For the owner-authorized 2026-10-19 existing-corpus replacement, use
`tools/regenerate_voice_corpus.py` and
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`. This scoped exception permits
replacing accepted runtime speech with new pending-review takes while retaining
isolated deterministic letters/syllables and originals for recovery. Per-character
tone/mood defaults and per-cue `delivery_prompt` use the existing VoiceEngine;
no child-runtime synthesis or second production backend is introduced.

Read:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

Canonical entry:

```bash
python3 tools/greia_voice.py doctor
```

All new production goes through VoiceEngine. As of the owner decision 2026-10-21, Dani, Momo and Tito use the selected v0.3 masters while Lilli, Leo and Flash retain their exact v0.2 IDs and bytes; shared local VoxStage/VoxCPM2 is the default and Chatterbox remains explicitly selectable. Dani’s compatible speech kind clones Dani; pedagogical pronunciation remains native/system. Start/reuse the installed `voxstage start` worker before the Greia readiness probe; use `voxstage unload` after production only when the shared worker is idle and this session is finished. New provider metadata and setup live in the voice-production skill and engine docs. Ordinary registry changes preserve accepted audio; the separate owner-authorized corpus operation replaced selected rows as listening-pending. The original accepted shared v0.2 baseline contained 180 reactions + 12 introductions; consult current per-cue acceptance after replacements; runtime resolver/product placement remain separate concerns. Launcher spoken labels are a separate accepted prerecorded Shell asset set.

## Progression / achievements / Badge Library

Read:

```text
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
docs/adr/0033-fail-soft-activity-crossbindings-and-dev-noise-scrub.md
runtime/progression-policy.toml
runtime/achievement-policy.toml
```

Absent-Activity cross-bindings fail soft where ADR 0033 specifies; corrupt policy and undeclared events remain hard failures.

## Performance / low-resource regressions

Read:

```text
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

Measure the interaction actually being optimized. Desktop reasoning is not Acer/Pi performance evidence.

## Physical Acer / developer remote-control work

Read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/testing/LOCAL_AGENT_START_HERE.md
```

Then follow the exact physical procedure named by `HANDOVER.md`.

## Visual-system / asset integration

Route to:

```text
skills/greia-visual-authoring/SKILL.md
```

Do not duplicate visual-authoring rules here.

## Completion check

Before calling substantive OS/platform work done, record:

```text
1. task-specific authorities read
2. exact source SHA changed/tested
3. tests/validators actually run
4. evidence lane exercised
5. what remains unverified
6. platform authority/resource invariants preserved
7. required plan/HANDOVER/manual/skill updates made
```

The standard is not maximal documentation. The standard is a small set of current, correct routers pointing to the real authority for the task.

## Fresh profile / first-boot ownership invariant

For installed-target profile work, the shared Parent-created directory contract
is load-bearing:

- `/var/lib/greia-profiles/data` is setgid `pipprofiles`;
- Parent-created profile roots, `customization`, and `activities` must be
  `2770` with the managed `pipprofiles` group **before** a profile is
  published;
- child-owned `progress` and `storage` are not Parent-precreated;
- the Parent unit currently uses `UMask=0007` so setgid inheritance produces
  the correct shared mode without weakening `RestrictSUIDSGID=yes`;
- never swallow a failed profile-directory permission repair.

First-profile setup (2026-10-17): `ProfileStore.ensure_initialized` marks its
placeholder in `profiles.json` (`first_profile_setup`); while only that
placeholder exists the child Shell runs the voiced setup wizard
(`greia_launcher.first_profile_*`, `docs/product/FIRST_BOOT_PROFILE_SETUP.md`)
and writes through `ProfileStore.complete_first_profile`; any ordinary
create/update/delete drops the marker. More children stay Parent-gated.

First-boot B4/B5 are compatibility migrations, not substitutes for correct
creation-time ownership. A physical first-boot acceptance must create/use a
profile after first-boot has completed and prove the child can create its own
progress/storage state.

The platform boot observer is semantic A/B infrastructure. Do not enable
`greia-boot-observer.service` on single-root layouts that have no installed
layout/release slot identity.

Developer status/log diagnostics must remain usable when the graphical display
is broken. Display-dependent operations such as screenshot/input still require
a valid bounded developer display endpoint.


### Activity launch feedback localization (2026-10-13 source WIP)

The Shell-owned `src/greia_launcher/launch_feedback.py`
is now the small typed owner of launch overlay, badge,
and wait phrases. Use the **effective child/profile UI
locale**, not process `LANG`, a new supported-language
list, or Activity-local duplicated phrases. The launcher
consumes the same source in the pre-READY overlay and
tile badge. Focused pure tests:
`tests/test_launcher_launch_feedback_localization.py`;
provider-free suite and display acceptance still pending.


### Activity launch hand-off (2026-10-17)

`LauncherApplication._launch_selected` (`src/greia_launcher/main.py`) presents the launch screen before `supervisor.start` (package validation, brokers and sandbox set-up used to run with no feedback), captures it as a `LaunchCard` and publishes it to `<activity data>/.greia/launch-card` (`greia_platform.activity_launch_cover.LaunchCardPublisher`; fail-soft, symlink-safe, discarded when the launch lifecycle returns). The Activity entry paints it right after the Activity's first `set_mode` and removes it; the Shell treats the missing card as "covered" and stops repainting its hidden wait screen. Keep that order (present, publish, start) and keep the card a raw frame of what the Shell shows, so the hand-off stays seamless; a future display backend (R7) can keep the same contract. READY timing is unchanged. The entry opens the Activity's first window `HIDDEN` and shows it with a second `set_mode(..., SHOWN)` before painting the card, because a window mapped by the first `set_mode` showed one black frame (51–83 ms on the Acer at 4d6e9c5e); keep both calls pure Pygame.

Home during the launch (ADR 0019 *Launch phase*): `TrustedChromeActivitySupervisor.start` prepares **and shows** the trusted chrome (`SystemChromeCoordinator.launch_started`) as soon as the session exists; `activity_ready` only restacks it. Before that, the Shell draws the backend's Home *picture* on its launch screen (`supervisor.paint_launch_home` → `SystemChromeCoordinator.paint_launch_picture` → optional backend `paint_launch_picture`; Legacy-X palette in `system_chrome_legacy_x.py`, pure-Pygame painter in `system_chrome_picture.py`), so the card carries it too. Home before READY (trusted chrome, a tap queued on the Shell's launch screen, or the controller guide button) calls `cancel_launch`: an immediate bounded `force_stop(FORCED_STOP)` of a process that has presented nothing; after READY Home stays the graceful stop. When the card is consumed (Activity window mapped) the Shell calls `ensure_system_chrome_visible` to raise Home again. A new chrome backend must keep: show at launch, restack at READY, optional picture. Tests: `tests/test_activity_launch_cover.py`, `tests/test_trusted_chrome_supervisor.py` (`LaunchPhaseHomeTests`), `tests/test_system_chrome.py`, `tests/test_system_chrome_legacy_x.py`. ADR 0037 §6a *Launch cover*.

Return tap guard: after any launch ends, the Shell ignores taps in the top-left Home/Back corner for 1.5 s (`greia_launcher.return_tap_guard`, wired in `main.py`/`presentation.py`), because a child's repeated Home tap otherwise lands on the Shell's profile button under the same spot and logs the profile out. Taps elsewhere act immediately. Test: `tests/test_launcher_return_tap_guard.py`.


### Launch-time package validation cost (2026-10-17)

`RuntimeManager.prepare_launch` still runs the runtime adapter's full package validation (Python: path policy, backend independence, curated import allowlist, dynamic-import rejection), but cheaper:

- `PythonRuntimeAdapter.validate_package` walks the tree once with `os.scandir` (`_python_package_sources`) and parses and walks each `.py` once. `greia_platform.activity_backend_policy.scan_python_source` returns the backend findings plus the `Import`/`ImportFrom`/`Call` nodes in `ast.walk` order, so the adapter no longer runs its own walk. The old code walked every AST three times; the walks, not `ast.parse`, were most of the cost. Findings and import nodes are identical to the old scanner (checked over every repo source).
- `greia_launcher.launch_validation_cache.LaunchValidationCache` (owned by the `RuntimeManager`, so one per Shell process, in memory only, LRU of at most 64 × 16-byte digests) skips re-validation when a package passed earlier in the same process and its stat fingerprint (`greia_platform.activities.package_tree_fingerprint`: path, type, size, mtime_ns, ctime_ns and inode of every entry; no content read) is unchanged. Any difference, or an error computing the fingerprint, runs the full validation again, and an edited package that still passes launches normally. The fingerprint is only a cache key, not anti-tamper. Failures are never cached. Only `BUILT_IN` trust in a root-owned tree this process cannot write qualifies (`read_only_built_in_package`), so the trust comes from the launch authority (`prepare_launch(..., package_trust=authority.package_trust)`). Parent, developer and writable-checkout packages are validated on every launch.
- Acer N270, standalone: full validation 0.7/1.2/1.2/7.5 s became 0.3/0.55/0.55/3.4 s (workshop_settings, colline_allegre, viaggio_delfino, enciclopedia_greia), and a reused validation takes 0.003–0.08 s. Through the Shell, tap→READY for enciclopedia_greia went from 14.0/13.4 s to 9.0 s on first launch and 5.0–7.0 s on repeats (PHYSICAL DEVICE, xdotool input, temporary overlay that has since been reverted).
- What still costs time is the first launch per Shell process (one `ast.parse` per file, about 2 s for enciclopedia_greia). A root-owned validation record written on the final installed tree (deploy/image step, the same place as the bytecode prefix) could remove it. That is not built: the built-in index is generated before tar/squashfs/installer copies, which change mtimes and inodes, so a fingerprint recorded in the index would not match on the device. Tests: `tests/test_launch_validation_cache.py`.


### Display-string API contract and render-path audit (2026-10-13)

`LocalizedResources.text(key, variables=None)` is the actual public
string lookup in `src/greia_platform/localization.py`; there is **no**
`LocalizedResources.string()` method. Calling `.string()` inside a
blanket-except helper is a silent multilingual rendering failure, not a
legitimate fallback. Runtime text placeholders use `string.Template`
(`$variable`), and the display result follows ADR 0034 child-case
presentation. Resolve Activity UI text at the Activity owner and pass
renderers the already-resolved labels; leave genuinely language-neutral
symbols for missing-package emergency rendering, and report missing
required translations as release blockers. The real My Time/Creations
local-agent acceptance queue remains `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`;
source key parity alone cannot certify translated runtime behavior.

## High-resolution layer, Wi-Fi resume hook and Parent API locking (2026-10-21)

- **High-resolution layer:** `src/greia_platform/hires_surface.py` is transparent to Activities; opt in with `PygameReferenceCanvas(hires=True)`. It activates at a CONTAIN scale of at least 1.2x (`HIRES_MIN_SCALE`), loads `@2x` art, and is disabled for diagnosis with `GREIA_ACTIVITY_HIRES=0`. Platform code that needs real pygame calls uses `RAW`, not the patched functions. Contract: `docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md` §9.3.
- **Wi-Fi resume hook:** `build/overlay/usr/lib/systemd/system-sleep/greia-wifi-resume` covers iwl3945, iwl4965, b43, b43legacy, brcmsmac, ath5k; after resume it waits for the interface and iwd station and reloads the driver only on failure. Not yet verified on the Aspire until reimage.
- **Parent API threading:** `src/greia_parent/production_api.py` serializes every request with a server-wide lock except the Wi-Fi scan/connect endpoints, which use a separate Wi-Fi lock so a slow association cannot freeze the panel.

## Installer single-root layout and EFI seam (2026-10-21, UNPROVEN)

The whole-disk installer no longer hard-codes its partition commands: `src/greia_installer/efi_boot.py` defines `SingleRootLayout` (`bios-single-ext4`, `uefi-or-bios-gpt-ext4`), `SysfsFirmwareProbe` and `plan_efi_boot`. `InstallationEngine._select_layout` picks the EFI layout only if the live installer booted via EFI and the target profile composed `boot-grub-efi`; BIOS machines keep the old command arrays. Add new firmware/boot variants as new layout classes or command plans there, not as `if` branches in `engine.install`. Target images carry only the `-bin` GRUB EFI packages (the non-bin ones conflict with `grub-pc`). Evidence is source and fake-runner tests only; see `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` section 14.

## Fresh A/B BIOS GRUB adapter (2026-10-24, SOURCE / UNPROVEN)

Fresh A/B installation has its own mandatory BIOS bootloader seam: production
composition injects `device_seams.build_bios_bootloader_installer` as
`FreshAbInstallSeams.bios_bootloader_installer` in
`src/greia_installer/fresh_ab_install.py`. The seam is required before erase
for the `grub-ab-v1` backend and runs only after the plan-derived boot-control
ext4 volume is verified and mounted, with its shared `grub.cfg` and default-A
`grubenv` checked. The adapter rechecks whole-disk identity immediately before
the array-only `efi_boot.bios_grub_install_command` call, placing BIOS GRUB's
core image/modules beside the shared config. Extend this seam rather than
adding another BIOS command path to `engine.install` or a fake GRUB success.
Focused source tests do not prove a boot: the external Session 04 work order
requires a blank-disk BIOS install followed by a real installed-disk boot
through BIOS GRUB into Greia. That predicate remains pending on Linux.


### 2026-10-22 voice priority continuation

The owner resumed the existing frozen 667 problematic short recordings through
`tools/finish_voice_priority.py`, wrapping VoiceEngine/CorpusRunner. It checks
installed takes and recovers saved providers before fresh, carries three-take
cumulative budgets and requires Base target score >0.8 with no signal warnings.
Read the voice-production skill and corpus manual for execution/recovery;
this does not authorize deferred retakes or accept new audio as human-reviewed.


Automatic short voice requests (2026-10-22): normal VoxStage speech now routes
≤4 words through localized carrier/cut/final-Base checks at VoiceEngine entry.
CLI/JSON/Python routing/word/character overrides live in the usage README; native
pedagogical speech stays excluded. Three total takes, no published failed target.
Explicit corpus raw synthesis bypasses auto wrapping to preserve frozen scripts.
The general separate verification queue is still proposed.


### 2026-10-22 correction: normal API v7; frozen corpus stopped

Normal automatic short requests now use `tools/voice_carrier_search.py` v7:
PCM-first bounded suffix candidates, no raw-intro ASR, exactly one target-only
Base match. The normal API uses score >0.8 plus equal canonical unit count and
identical numeric sequence; exact locale words/digits 0–100 are equivalent.
Final delivered signal/ASR checks remain mandatory unless explicitly disabled.
ASR/IO failures require recovery and must not spend a fresh take. See the
VoiceEngine README and `docs/reviews/2026-10-22_TARGET_ONLY_VOICE_EXTRACTION_V7.md`.
The historical 667-cue producer remains stopped on v6; never resume unchanged.
A versioned corpus adapter must preserve source/master/job provenance and
cumulative budgets before any synthesis or installation. Saved replay candidates
are external and listening-pending, not installed or human-approved.

V7 corpus saved-source recovery now has a no-synthesis adapter:
`tools/recover_voice_candidates.py` (stage, then `--install` the same completed
external folder). Existing CorpusRunner/RunStore own installation/backups and
human_review stays PENDING. Frozen corpus v6 producers remain stopped; consult
the voice skill/corpus manual before any further work.

Authoring speech update2026-10-22: normal short intros now use a period and warm
clear careful-reading defaults. The final-take corpus adapter uses normal
VoiceEngine, required verification, one remaining cumulative take and existing
transactions; infrastructure uncertainty stops for exact-job recovery using
GenerationResult.evidence_dir. The220-file v2 plan is prepared but not started:
12 live prompt probes8PASS/4rejected miss readiness. Read current HANDOVER/voice
skill before execution. HTTP response timeout now defaults120s independently of
job wait; never repeat an uncertain POST or restart the shared VoxStage worker.


Owner method-repair correction2026-10-22: corpus final-take-v7-02 is OWNER
STOPPED, not prepared/unstarted or runnable. Automatic continuation is deleted.
Owner permits bounded diagnostics on two consistently rejected targets only.
Current comparison v2 supports standard cardinals0–100 EN/IT/FR/ES, guards exact
numeric values/literals and removes internal-marker score inflation. Normal
Whisper verification and review/reassess v4 share it; historical v1 evidence
is retained. Source preparation and alternate natural-carrier prompts remain
experimental, not production defaults. Read HANDOVER and paired-method report;
no bulk restart or threshold relaxation follows from a small diagnostic result.


Natural completion update2026-10-22: owner authorized a new bounded natural-
method run for247 unresolved priority cues. It injects NaturalCarrierPolicy and
MethodAttemptBudget into existing ShortPhrasePipeline, with up to3actual new
calls and historical counters retained. Existing transactions install only final
Base/count/number/signal passes, human pending. Initial real-corpus canary hit
METHOD_REVIEW_REQUIRED (2installed,3exhausted,242unstarted); do not blindly resume.
Read docs/agents/GREIA_NATURAL_VOICE_COMPLETION.md and HANDOVER for active method
repair. Alternate policy selection is explicit; normal API defaults unchanged.


Current voice continuation correction2026-10-22: BOTH natural producers are held
for poor yield; do not restart natural-context-v1 or natural-context-speech-v1.
Latest exact audit7installed pending,240remaining. Explicit saved-only English spoken
comparison can recover homophonic recognition errors without another provider
call; normal API defaults and historical policies remain unchanged. Read the
current natural completion guide/HANDOVER for diagnostic state and remaining
lists. A failed prompt experiment never authorizes a blind bulk continuation.


2026-10-22 context safety correction: the82-source packaged-context experiment
failed on an uncut-intro OGG false approval. Neither context version is selected.
Two additional saved diagnostic takes pass unchanged isolated checks and were
installed pending through existing transactions; no new synthesis/default change.
Current7installed/240remaining, all actual corpus/diagnostic calls retained. Follow
PACKAGED_CONTEXT_SAFETY_REVIEW and HANDOVER for optional saved-WAV scope; never
restart held producers or claim failed experimental gates passed.


## A/B installer initial device preferences (2026-10-29; source only)

Fresh A/B install seeds the authorized locale and hardware settings in the
PERSIST device-settings namespace, and copies the selected tested iwd profile
into network-state on a best-effort basis. First boot assigns seeded settings
files to the Parent identity before child/Parent services start. These source
changes need a rebuilt image and installed validation. The reported Acer Parent
service outage remains undiagnosed; the revised unavailable message is not
evidence of a repaired service.


## Live installer SSH (owner decision 2026-10-29; source/demo)

The Wi-Fi page owns a live-installer SSH toggle, off by default on ordinary
installer images (`greia` /
`greia`, ordinary password sudo). The fixed local installer transaction
operations start/stop only live `ssh.service`; this does not enable SSH on the
installed release. Use the existing Linux USB patch work order for physical
acceptance; the installer demo and screenshot renderer do not prove networking.

---
name: greia-os-work
description: Task router for substantive Greia OS/platform/Shell/Parent/installer/simulator/build/runtime/hardware-service work. Load only the task-specific local docs required for the work.
---

# Greia OS Work — task router

**Status:** LIVING derived contributor router  
**Reviewed:** 2026-09-21

This file tells an agent **what to read for the task**. It is deliberately not a second architecture manual.

## Universal rules

1. Work from current `main`; preserve concurrent changes. Read `AGENTS.md` and `HANDOVER.md` first.
2. Accepted ADRs own architecture; source/runtime declarations own exact implemented APIs/schemas/limits; product docs own accepted child-facing behavior.
3. Greia Shell is the child-facing OS surface. Do not expose a generic Linux desktop/shell/package-management path during normal child use.
4. Platform authority stays platform-owned: profiles/sessions, trust/packages, permissions, Home/Back, physical input, system controls, microphone routing/processing, storage/history, progression/rewards, install/update authority and hardware facts.
5. Low-resource behavior is correctness. The Acer reference floor is not a later optimization target.
6. GitHub-hosted Actions/execution are opt-in only and require explicit owner authorization.
7. Claim only evidence that actually ran. Source, authoring-provider+human, browser, Simulator, VM/image and physical evidence are distinct.
8. After substantive implementation, update the active plan/HANDOVER and affected living manuals/skills as required by `AGENTS.md`.
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

## Current blocking route: post-R1 product-composition closure + multiplatform lifecycle plan

Install/update/release/multiplatform lifecycle work routes to
`docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`
(the ADR 0036 successor plan), not to signed-bundle or Gate-P5/V12G/D6
closure. That plan owns lifecycle sequencing and closure criteria; the
2026-08-08 architecture-remediation plan remains blocking only for its
remaining non-lifecycle obligations.

Session 03's owner-release CLI implementation and source validation are green.
The current lifecycle entry point is the **real Linux owner-command release
build acceptance**:

`docs/testing/2026-09-21_SESSION03_LINUX_RELEASE_BUILD_ACCEPTANCE.md`

Run that only on an owner-approved x86_64 Linux build host. It proves the
single owner command against the current Acer-only release matrix; it does not
create or certify the universal Setup image, which remains Session 08 work.

The old signed `.greiaupdate` v2 flow and release signing keys are
superseded by ADR 0036 and are not the normal production route; older
references to them are historical only.

After the Session 03 Linux owner-command build is green, Session 04 owns the
real legacy-i386 fresh-install/update/rollback lifecycle. The
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

## Supported-language declaration and staged ES/FR translation

The current **selectable** OS device locales are `en` and `it` only.
The former 12-language installer/on-device/Parent API roster has been
reduced at its unique owner `src/greia_platform/system_language.py`.
Spanish and French are actively staged but NOT selectable until
installer, Shell, Parent HTML/overlay, built-in Activities, media and
source/physical acceptance pass. Follow
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`
and `LOCAL_AGENT_VOICE_PRODUCTION.md` in that directory.
`src/greia_installer/i18n_es_fr.py` contains staged copy; never
misinterpret it as a shipped Spanish/French install-flow claim.
Historical unsupported records are left intact and read as safe
English runtime fallback. Do not install voice/TTS models on Greia OS.
New authoring-time provider adapters belong only under
`tools/greia_voice_core`, with Modal a proposed authoring backend,
not a current runtime feature.

### Installed Parent locale translation seam (2026-10-13)

On-device Parent Settings `ParentSettingsOverlay` renders semantic
password/authentication, eight tabs, title and device language controls
via `src/greia_launcher/panel_localization.py`. This is source-staged
for EN/IT/ES/FR; only EN/IT are currently selectable globally.
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

Current lifecycle authority is ADR 0036 plus the 2026-09-15 lifecycle plan:

```text
docs/adr/0036-unified-system-slot-releases-and-platform-install-media.md
docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md
```

Historical context only (signing requirements superseded by ADR 0036; the
signed `.greiaupdate` v2 / release-key workflow is not the normal
production route):

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

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

All new production goes through VoiceEngine. Current accepted shared v0.2 assets contain 180 shared reactions + 12 introductions; runtime resolver/product placement remain separate concerns. Launcher spoken labels are a separate accepted prerecorded Shell asset set.

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

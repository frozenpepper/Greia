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

## Protected Activity Home/Back and lifecycle chrome

Read:

```text
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/reviews/2026-08-29_R7_R73_ACTIVITY_CHROME_MIGRATION_TRANCHE.md
docs/reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md
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
build/overlay/etc/systemd/network/         (wired vs wireless ownership)
build/lib/compose.sh                       (compose_configure_systemd enable lists)
```

**`iwd` owns the wireless link. `systemd-networkd` owns wired DHCP only.** Greia
ships no `wpa_supplicant`, so iwd is the only WPA2-capable path in the product.
Three traps, all of which have actually bitten this project:

- **`systemd-networkd` must never claim a wireless interface.** iwd only publishes
  its `Device`/`Station` D-Bus interfaces while it holds the adapter in *station
  mode*, and it will not take a link networkd manages. A `Name=wl*` + `DHCP=yes`
  policy makes the installer report the card while never listing a network, and it
  cannot join an encrypted network anyway. Wireless policies use
  `[Network] Unmanaged=yes` to state the boundary explicitly rather than merely
  failing to match.
- **Do not probe iwd as `su nobody`.** iwd's bus policy allows `root` and group
  `netdev`. `su` does not inherit systemd `SupplementaryGroups`, so a `su` probe
  returns `Access denied` even when the real service reaches the bus fine. Probe
  with `setpriv --groups=$(getent group netdev | cut -d: -f3)`, or trust the
  installer's own report.
- **The installer persists iwd `.psk`/`.open` profiles into the target**
  (`engine.py` → `request.wifi_profile.write_to`). Changing wireless ownership
  in a way that starves iwd of station mode silently breaks installed first boot,
  not just the installer UI.
- **iwd owns `/var/lib/iwd`. Never write into it from an unprivileged
  process.** It is `root:root 0700`; the installer is `User=nobody`, so any
  attempt fails with `[Errno 1] Operation not permitted`. To hand iwd a
  passphrase, register a `net.connman.iwd.Agent` and answer
  `RequestPassphrase(object network) -> string`; iwd persists the profile
  itself. Same class as the link conflict: the resource belongs to iwd.
- **Two iwd-agent traps, both found only on real hardware.** The image's
  python3-dbus rejects the three-argument `dbus.Interface(bus, path, iface)`
  form with `TypeError` — use `bus.get_object(...)` then
  `dbus.Interface(proxy, iface)`, the shape the rest of `wifi.py` already uses.
  And `dbus.SystemBus()` is a shared singleton the scan path already opened
  with **no main loop**, so exporting an object on it raises "connections must
  be attached to a main loop"; the agent needs its own `BusConnection` with an
  explicit main loop, and should answer only for the selected network's object
  path.

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
docs/reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md
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

## Microphone/audio capture processing

Read:

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
docs/reviews/2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md
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

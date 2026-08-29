---
name: greia-os-work
description: Task router for substantive Greia OS/platform/Shell/Parent/installer/simulator/build/runtime/hardware-service work. Load only the task-specific local docs required for the work.
---

# Greia OS Work — task router

**Status:** living derived contributor router  
**Reviewed:** 2026-08-29

Keep this file small. It tells an agent **what to read for the task**; it is not a second architecture manual.

## Universal rules

These apply to substantive OS/platform work:

1. Work from current `main`; preserve concurrent work. Read `AGENTS.md` and `HANDOVER.md` before changing implementation.
2. Accepted ADRs own architecture; source/runtime declarations own exact implemented APIs/schemas/limits; product docs own accepted child-facing behavior. Do not resolve contradictions by choosing convenient prose.
3. Greia Shell is the child-facing OS surface. Do not expose generic Linux desktop/shell/package-management UI in normal child operation.
4. Platform authority stays platform-owned: profiles/session, trust/packages, permissions, Home/Back, physical input, **microphone routing/processing**, storage/history, progression/rewards, install/update authority and hardware facts. The physically accepted microphone contract is lightweight cleanup by default, on-demand, with Parent-owned disable/advanced preferences; Activities consume the route and do not own DSP/device policy.
5. Low-resource behavior is correctness. The reference Acer remains a real engineering floor; do not introduce heavyweight hot-path work without evidence. Preserve the accepted microphone route's zero-idle-cost character unless new evidence justifies a different platform design.
6. Never use GitHub-hosted Actions or paid/hosted execution unless the owner explicitly authorizes that specific use.
7. Claim only evidence that actually executed. Source tests, simulator evidence, VM/image evidence, authoring-provider/audio evidence and physical-device evidence are different lanes.
8. After substantive implementation, update the active plan and `HANDOVER.md` as required by `AGENTS.md` and keep this router/companions synchronized when contributor workflow changes.
9. New prerecorded Greia speech production is authoring-time work and must use the canonical Voice Production Engine. OS/shared-library scripts must not grow a parallel Chatterbox/native-TTS/Whisper implementation.
10. Display/session/input abstraction must preserve performance. Activities remain backend-neutral while SDL/Pygame keeps direct rendering and safe high-rate input paths; backend-specific acceleration belongs below the trusted Greia boundary. Do not introduce a generic Python framebuffer proxy, avoidable full-frame copies, high-rate pointer/text IPC, or continuously redrawn full-screen trusted chrome merely to make Xorg/Wayland/KMS implementations look identical.

Before installing/configuring any toolchain, build host, simulator dependency, Parent checkout, developer-remote environment or voice provider, read:

```text
SETUP.md
```

For repository/test-hardware operating procedure, read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
```

## Read by task

### Broad architecture or new platform seam

Read:

```text
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/adr/0012-platform-architecture-constitution.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

Use this broad set only for genuinely cross-cutting architecture work. Prefer narrower authorities below for ordinary subsystem changes.

### Boot, GRUB, Syslinux, initramfs, first boot, X startup, image boot/recovery

Read **first**:

```text
skills/greia-os-work/BOOT.md
```

Then:

```text
docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/design/GREIA_BOOT_EXPERIENCE.md
docs/design/GREIA_BOOT_PROGRESS.md
```

Do not modify physical boot/recovery state from memory. `BOOT.md` owns the recovered Acer safety procedure, SSH/recovery invariants, change-scoped regeneration and pre-reboot gates.

### Installer, image composition or build pipeline

Read:

```text
docs/adr/0013-image-composition-and-package-architecture.md
docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md
docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md
SETUP.md
```

Inspect exact current builders under `build/` before changing generated target state. Boot-impacting changes also require `skills/greia-os-work/BOOT.md`.

If image/build work affects audio packages, ALSA composition, the Greia microphone ExtPlug or endpoint-readiness service, also read the audio/microphone section below. A fresh image must either provide a genuinely working lightweight endpoint or fall back honestly; never ship a readiness marker without a real capture probe.

### Shell, launcher, Collections or lightweight UI

Read:

```text
docs/adr/0018-lightweight-ui-foundation.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Inspect current source owners under:

```text
src/greia_launcher/
src/greia_platform/ui_*.py
```

Collections provide semantic data; do not create category-specific copies of shared Shell/pagination/panel behavior.

### Protected Activity Home/Back and lifecycle chrome

Read:

```text
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
```

### Input, controller, pointer or touch ownership

Read:

```text
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/testing/2026-08-15_PHASE0_INPUT_CONTROLLER_ACCEPTANCE.md
```

### Responsive display, viewport, canvas or coordinate-space work

Read:

```text
docs/adr/0026-resolution-adaptive-ui-layout.md
docs/adr/0027-activity-coordinate-spaces-canvas-and-world-camera.md
docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md
```

### R7 display/session backend or backend-independence work

Read:

```text
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
src/greia_launcher/display_session.py
src/greia_launcher/display_session_legacy_x.py
src/greia_launcher/system_chrome.py
src/greia_platform/activity_backend_policy.py
```

Preserve the existing seams rather than inventing a parallel platform layer. `DisplaySessionCoordinator` owns shell/Activity surface lifecycle; concrete backends own Xorg/Wayland/KMS-private mechanics. Activity source stays backend-neutral and may continue using ordinary SDL/Pygame rendering/performance techniques. `tools/audit_activity_backend_independence.py` inventories blockers and temporary migration debt. A backend is not acceptable merely because it is architecturally tidy: measure the exact user-visible path and preserve the Acer-class performance envelope.

### Activity runtime, package, permissions, trust or lifecycle integration

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

For Activity implementation itself, switch to:

```text
skills/greia-activity-authoring/SKILL.md
```

Installed Activity availability is an **OS-owned containment contract**, not an agent-discipline contract. Per ADR 0033, the installed service performs a narrow privileged pre-launch scrub of curated regenerable host/cache noise across discoverable Activity roots, then the unprivileged registry isolates real broken packages. Runtime progression/achievement enrichment must not become launcher availability authority. Do not move this responsibility into individual Activities, make the launcher run as root, broaden the deletion vocabulary into general “cleanup”, or weaken strict source/build Activity/policy validation.

Explicit developer-image built-in replacement remains platform-owned and fail-closed. `greia-devctl --replace-system` resolves the target by exact validated canonical manifest identity through `ActivityRegistry`; it must not derive a path from display title, slug, alias or directory name. Preserve backup/state/restore and `BUILT_IN` versus `DEVELOPER_UNSIGNED` trust boundaries.

### Activity Simulator

Read:

```text
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
```

Simulator evidence does not prove physical hardware/session/backend behavior.

### Parent management, Parent API/client or pairing/device management

Read:

```text
docs/architecture/GREIA_PARENT_MANAGEMENT.md
docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md
```

Inspect the current Greia Parent API/source pin and external Parent client revision before changing either side. Do not bypass capability discovery or platform authority with SSH/shell/file-copy shortcuts.

For microphone controls, preserve:

```text
Improve microphone sound = Parent-owned microphone_processing_enabled
OFF -> raw/off route on next microphone open
Restore defaults -> lightweight processing desired, advanced false
Advanced -> visible/selectable only when a real advanced endpoint is available
```

An Activity must not mutate these Parent settings on its own behalf.

### System update mechanism

Read:

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

### Progression, achievements, Stars or Badge Library

Read:

```text
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
docs/adr/0033-fail-soft-activity-crossbindings-and-dev-noise-scrub.md
runtime/progression-policy.toml
runtime/achievement-policy.toml
```

A progression/history/achievement policy rule referencing an Activity absent from the loaded catalogue drops that rule at runtime with a warning instead of raising. Undeclared events on a loaded Activity and structural policy corruption still fail hard. Built-in Activity trees are scrubbed of curated regenerable dev-noise before discovery; genuinely broken Activities are never auto-healed.

Inspect current history/achievement/event-broker source owners before changing policy or presentation.

### Localization, language presentation, profile grammatical agreement or child text letter case

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

Child-facing UI text defaults to CAPITAL letters under ADR 0034. `LocalizedResources.text()` and Shell child-facing render chokepoints apply it automatically; parent-facing surfaces and child-authored content bypass it deliberately.

### Audio service or microphone capture/processing

Read:

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md
docs/reviews/2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md
skills/greia-activity-authoring/MICROPHONE_RECORDING.md   # when Activity-facing use changes
```

Current accepted product/platform contract:

```text
ordinary child voice capture
  -> audio.basic authority
  -> Greia-owned microphone route
  -> lightweight cleanup by default when endpoint is healthy
  -> zero-idle-cost/on-demand processing
```

This is an available platform facility, not an experimental feature Activities should avoid.

Preserve:

- no automatic processor selection/promotion;
- advanced processing is optional and Parent-selected only when available;
- `microphone_processing_enabled = false` resolves to raw/off on next microphone open;
- ordinary Activities cannot bypass Parent policy by opening physical ALSA hardware;
- genuine raw-signal requirements need a typed platform/API extension;
- broken lightweight backend fails honestly to raw with truthful reason;
- readiness markers represent current-boot endpoint probes, never source presence;
- non-`audio.basic` Activities receive no route environment;
- physical card/codec identity stays below Greia-owned composition;
- do not reintroduce an always-running heavy audio service for convenience.

For first-party Activity recording behavior switch to `skills/greia-activity-authoring/SKILL.md` + `MICROPHONE_RECORDING.md`.

### Voice/speech asset production tooling

All new prerecorded Greia speech production uses the authoring-time Voice Production Engine.

Read:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

Canonical entry point:

```text
tools/greia_voice.py
```

Before actual production run:

```bash
python3 tools/greia_voice.py doctor
```

Only when installing/troubleshooting the optional authoring providers, read:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

The low-level Chatterbox field guide is for Voice Engine maintainers/troubleshooting only, not ordinary OS/shared-library production.

OS/shared-library scripts must not call Chatterbox, MLX, Whisper, native `say`/`afconvert`, FFmpeg trimming or canonical references directly. If a historical producer does so and needs new work, migrate it to a thin semantic `VoiceEngine` client.

Shared-library production uses `kind=shared_character_utterance`; Dani routes through the system provider. Normal Activities consume reviewed shared assets and do not synthesize them on the child.

Generated presenter speech and child microphone recording are different systems. Do not confuse build-time voice production with runtime `audio.basic` capture.

### Performance optimization or low-resource regressions

Read:

```text
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

Measure the interaction actually being optimized. Desktop/source reasoning is not Acer/Pi performance evidence. For R7/backend work, preserve direct SDL presentation, dirty/invalidation rendering, bounded caches and safe direct high-rate input; backend-specific fast paths are valid below the common semantic contract.

### Physical Acer / developer remote-control testing

Read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/testing/2026-08-15_ACER_REMOTE_AGENT_ACCEPTANCE.md
```

If the task touches microphone processing, also use the current audio-service physical evidence/protocol above. If it touches boot/reboot/recovery, `skills/greia-os-work/BOOT.md` is additionally mandatory.

### Visual-system or asset integration work

Route to:

```text
skills/greia-visual-authoring/SKILL.md
```

Do not duplicate visual authoring rules here.

## Completion check

Before calling substantive OS/platform work done, record:

```text
1. Which task-specific authorities were read?
2. What exact source SHA/state was changed/tested?
3. Which source tests/validators actually ran?
4. Which evidence lane was exercised: source / authoring-provider+listening / simulator / VM-image / physical device?
5. What remains unverified?
6. If audio/microphone changed: does audio.basic still receive only the platform route, does Parent OFF still apply on next open, and is readiness truthful?
7. If prerecorded speech was produced: did it go through VoiceEngine, retain human-review authority, and avoid adding child-runtime model dependencies?
8. Were required active-plan/HANDOVER/manual/skill updates made?
9. If display/session/input changed: is Activity source still backend-neutral, is trusted authority outside Activities, and were existing low-resource optimization opportunities preserved rather than hidden behind a slow common path?
```

Do not load broad architecture documents just because they exist. Start with this router, read the narrow authorities for the actual task, and expand only when the change genuinely crosses subsystem boundaries.
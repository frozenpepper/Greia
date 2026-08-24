---
name: greia-os-work
description: Task router for substantive Greia OS/platform/Shell/Parent/installer/simulator/build/runtime/hardware-service work. Load only the task-specific local docs required for the work.
---

# Greia OS Work — task router

**Status:** living derived contributor router  
**Reviewed:** 2026-08-24

Keep this file small. It tells an agent **what to read for the task**; it is not a second architecture manual.

## Universal rules

These apply to substantive OS/platform work:

1. Work from current `main`; preserve concurrent work. Read `AGENTS.md` and `HANDOVER.md` before changing implementation.
2. Accepted ADRs own architecture; source/runtime declarations own exact implemented APIs/schemas/limits; product docs own accepted child-facing behavior. Do not resolve contradictions by choosing convenient prose.
3. Greia Shell is the child-facing OS surface. Do not expose generic Linux desktop/shell/package-management UI in normal child operation.
4. Platform authority stays platform-owned: profiles/session, trust/packages, permissions, Home/Back, physical input, microphone routing, storage/history, progression/rewards, install/update authority and hardware facts.
5. Low-resource behavior is correctness. The reference Acer remains a real engineering floor; do not introduce heavyweight hot-path work without evidence.
6. Never use GitHub-hosted Actions or paid/hosted execution unless the owner explicitly authorizes that specific use.
7. Claim only evidence that actually executed. Source tests, simulator evidence, VM/image evidence and physical-device evidence are different lanes.
8. After substantive implementation, update the active plan and `HANDOVER.md` as required by `AGENTS.md` and keep this router/companions synchronized when contributor workflow changes.

Before installing/configuring any toolchain, build host, simulator dependency, Parent checkout, developer-remote environment or voice backend, read:

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

Then the relevant exact authorities:

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

Inspect the exact current builders under `build/` before changing generated target state. Boot-impacting changes also require `skills/greia-os-work/BOOT.md`.

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

### Activity runtime, package, permissions, trust or lifecycle integration

Read:

```text
docs/architecture/GREIA_ACTIVITY_ECOSYSTEM.md
docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md
docs/adr/0017-platform-owned-sessions-events-progression-and-reward-ledger.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0023-open-activity-ecosystem-distribution-and-official-catalogue.md
runtime/child-runtime.toml
src/greia_launcher/runtime_adapter.py
src/greia_platform/activities.py
src/greia_platform/activity_packages.py
src/greia_platform/trust.py
```

For Activity implementation itself, switch to:

```text
skills/greia-activity-authoring/SKILL.md
```

Explicit developer-image built-in replacement remains a platform-owned,
fail-closed operation. `greia-devctl --replace-system` resolves the target by
an exact validated canonical manifest identity through `ActivityRegistry`; it
must not derive a path from a display title, slug, legacy alias or directory
name. Use the same owner for replacement backup/state/restore and preserve the
`BUILT_IN` versus `DEVELOPER_UNSIGNED` trust boundary.

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

Inspect the current Greia Parent API/source pin and the external Parent client revision before changing either side. Do not bypass capability discovery or platform authority with SSH/shell/file-copy shortcuts.

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
runtime/progression-policy.toml
runtime/achievement-policy.toml
```

Inspect current history/achievement/event-broker source owners before changing policy or presentation.

### Localization, language presentation or profile grammatical agreement

Read:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/adr/0032-profile-presentation-and-grammatical-agreement.md
src/greia_platform/localization.py
src/greia_platform/language_presentation.py
src/greia_platform/profile_presentation.py
```

### Audio service or microphone capture/processing

Read:

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md
```

### Voice/speech asset production tooling

Read:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

Only read/install the local production toolchain when actual voice production is requested:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

### Performance optimization or low-resource regressions

Read:

```text
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

Measure the interaction actually being optimized. Desktop/source reasoning is not Acer/Pi performance evidence.

### Physical Acer / developer remote-control testing

Read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/testing/2026-08-15_ACER_REMOTE_AGENT_ACCEPTANCE.md
```

If the task touches boot/reboot/recovery, `skills/greia-os-work/BOOT.md` is additionally mandatory.

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
4. Which evidence lane was exercised: source / simulator / VM-image / physical device?
5. What remains unverified?
6. Were required active-plan/HANDOVER/manual/skill updates made?
```

Do not load broad architecture documents just because they exist. Start with this router, read the narrow authorities for the actual task, and expand only when the change genuinely crosses subsystem boundaries.

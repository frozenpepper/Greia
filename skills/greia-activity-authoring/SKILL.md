---
name: greia-activity-authoring
description: Task router for creating, modifying, refactoring, validating, packaging and testing Greia Activities. Load only the task-specific local docs required for the work.
---

# Greia Activity Authoring — task router

**Status:** living derived contributor router  
**Reviewed:** 2026-08-24

Keep this file small. It tells an agent **what to read for the task**; it is not a duplicate Activity manual.

## Universal rules

These apply to all substantive Activity work:

1. An Activity runs under Greia platform authority. Do not bypass platform lifecycle, storage, permissions, progression, Home/Back, input or runtime policy.
2. First-party implementation must remain maintainable: thin `main.py`, cohesive modules/classes, composition over procedural sprawl, reuse Greia platform primitives before inventing local frameworks.
3. Do not widen security/runtime policy merely to make one Activity convenient. Package-local code is Activity code; unknown external dependencies remain forbidden unless platform policy deliberately changes.
4. **Every new Activity must explicitly decide its child-facing presenter/character and speech plan.** Greia's recurring cast should normally be considered as social anchors, guides, reactions and curiosity hosts; omission must be deliberate, not accidental.
5. **Subject-rich Activities must explicitly consider an optional researched curiosity/facts interaction.** When appropriate, use short, well-sourced, child-safe facts delivered through multilingual-ready semantic cues and, where voice is part of the feature, reviewed localized speech.
6. **A new or substantively changed Activity is not done until the final runtime-relevant source state passes the real Greia Simulator launch/survival gate.** Source validation, imports, unit tests, `make verify`, `python main.py`, or package validation do not replace this.
7. Simulator launch evidence becomes stale after any runtime-relevant edit. Relaunch the final state.
8. If the simulator cannot be run, report `INTEGRATION-UNVERIFIED` / `SOURCE-VERIFIED / SIMULATOR-UNVERIFIED`; do not call the Activity complete or working.
9. Claim only evidence that actually executed. Simulator evidence is not physical Acer/Pi evidence.

For presenter/voice/fact design, read:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

For the exact mandatory launch procedure and failure criteria, read:

```text
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

An `ImportError`, `ModuleNotFoundError`, startup exception, immediate exit, dead first frame, first-interaction crash, or failure to return cleanly to the Shell is **failed Activity acceptance**.

## Read by task

### Creating a new Activity

If the Activity is governed by a current named product/design/implementation plan, read that Activity-specific specification first for **what the Activity must do**. Then read:

```text
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
docs/architecture/GREIA_ACTIVITY_ECOSYSTEM.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
```

A new Activity design must record:

```text
lead presenter/mascot or deliberate none
speech/shared-utterance plan
whether optional curiosity facts fit the subject
supported locales / multilingual speech plan
```

Do not treat voice as something to consider only after the Activity is otherwise finished.

For Python/runtime/import work also inspect current source authority:

```text
runtime/child-runtime.toml
src/greia_launcher/runtime_adapter.py
src/greia_platform/activity_api.py
src/greia_platform/activities.py
```

### Changing existing Activity code

Read:

```text
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

If the change affects character presence, speech, audio, knowledge/facts, localization or child-facing presentation, also read:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

### Refactoring or splitting an existing Activity

Read:

```text
skills/greia-activity-authoring/REFACTORING.md
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

The launch gate is mandatory after the **final** refactor edit. A clean architecture that fails in the Simulator is a failed refactor.

### Manifest, Collection, age/difficulty or discovery work

Read:

```text
skills/greia-activity-authoring/DISCOVERY.md
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
src/greia_platform/activities.py
src/greia_platform/activity_discovery.py
src/greia_launcher/catalogue_view.py
```

If runtime-relevant manifest data changed, also run `LAUNCH_ACCEPTANCE.md`.

### UI, layout, canvas, responsive or input work

Read:

```text
docs/adr/0018-lightweight-ui-foundation.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/adr/0026-resolution-adaptive-ui-layout.md
docs/adr/0027-activity-coordinate-spaces-canvas-and-world-camera.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md
```

For Pygame Activities inspect current shared primitives instead of copying launcher code:

```text
src/greia_platform/pygame_ui.py
src/greia_platform/pygame_canvas.py
src/greia_platform/activity_ui.py
src/greia_platform/activity_viewport.py
src/greia_platform/responsive_layout.py
```

Runtime-relevant UI/input work must finish with `LAUNCH_ACCEPTANCE.md`.

### Victory, completion, results, Continue or Play Again work

Read:

```text
skills/greia-activity-authoring/TERMINAL_RENDERING.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

Exercise the completion/restart path, not just startup.

### Achievements, Stars, score or completion events

Read:

```text
skills/greia-activity-authoring/ACHIEVEMENTS.md
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
runtime/progression-policy.toml
runtime/achievement-policy.toml
```

If event-emitting runtime code changed, also run `LAUNCH_ACCEPTANCE.md` and exercise the event-producing path.

### Packaging, install or `.greiaactivity` work

Read:

```text
docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md
src/greia_platform/activity_package_format.py
src/greia_platform/activity_packages.py
src/greia_platform/activity_assets.py
src/greia_platform/trust.py
```

Use the Simulator's canonical package-install path for package acceptance; then follow `LAUNCH_ACCEPTANCE.md`.

Developer-image built-in replacement is a separate platform control path, not an Activity package shortcut. The privileged owner resolves an installed target only from one validated canonical manifest identity through the shared Activity registry, preserving exact path safety, backup/restore state and the `BUILT_IN` versus `DEVELOPER_UNSIGNED` trust distinction. Never infer a target from a title, slug, legacy alias or directory name.

### Localization, language or grammatical agreement

Read:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/adr/0032-profile-presentation-and-grammatical-agreement.md
src/greia_platform/localization.py
src/greia_platform/language_presentation.py
src/greia_platform/profile_presentation.py
```

For spoken/localized presenter or fact content also read `PRESENTERS_AND_CURIOSITY.md` and `VOICE_GENERATION.md`.

If visible/runtime resources changed, finish with `LAUNCH_ACCEPTANCE.md` in the materially affected locale/profile configuration.

### Character presenter, speech, pedagogical speech, facts or voice generation

Read:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

Only read the local production setup when actual custom voice production/configuration is required:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

### Microphone/capture work

Read:

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
src/greia_platform/audio.py
src/greia_platform/activity_api.py
```

Do not implement Activity-local device selection or DSP policy.

### Performance optimization

Read:

```text
skills/greia-activity-authoring/ENGINEERING.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

Then rerun `LAUNCH_ACCEPTANCE.md` because an optimized Activity that no longer launches is not an optimization. Hardware performance claims require named physical hardware and exact source SHA.

### Broad cross-cutting Activity work

Only when the task genuinely spans several of the areas above, use:

```text
skills/greia-activity-authoring/CORE.md
```

`CORE.md` is **not mandatory first reading for every Activity task**. Prefer the narrower files above.

## Completion check

Before saying substantive Activity work is done, answer:

```text
1. Which task-specific docs above were read?
2. For a new Activity: what presenter/speech/curiosity-fact decision was made?
3. Which source/test validation actually ran?
4. What exact final source SHA/state was launched through Greia Simulator?
5. Did it reach a usable frame, survive >=10s, survive meaningful input, and return cleanly to Shell?
```

If #4 or #5 has no successful evidence, the correct status is **integration-unverified**, not complete.

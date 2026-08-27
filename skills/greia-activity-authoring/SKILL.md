---
name: greia-activity-authoring
description: Task router for creating, modifying, refactoring, validating, packaging and testing Greia Activities. Load only the task-specific local docs required for the work.
---

# Greia Activity Authoring — task router

**Status:** living derived contributor router  
**Reviewed:** 2026-08-28

Keep this file small. It tells an agent **what to read for the task**; it is not a duplicate Activity manual.

## Universal rules

These apply to all substantive Activity work:

1. An Activity runs under Greia platform authority. Do not bypass platform lifecycle, storage, permissions, progression, Home/Back, input or runtime policy.
2. First-party implementation must remain maintainable: thin `main.py`, cohesive modules/classes, composition over procedural sprawl, reuse Greia platform primitives before inventing local frameworks.
3. Do not widen security/runtime policy merely to make one Activity convenient. Package-local code is Activity code; unknown external dependencies remain forbidden unless platform policy deliberately changes.
4. Installed Activity-tree sanitation and broken-package containment are **platform responsibilities** under ADR 0033. Do not add Activity-local cleaners for host/cache files, make an Activity self-repair its package, or weaken package validation because an installed development tree became dirty. The installed OS removes only curated regenerable noise; genuine defects remain isolated package failures.
5. **Assume the target child may not be able to read. Core gameplay instructions, retry guidance, navigation and completion must not depend on written text.** Design the Activity so the next action is visually obvious; use large icons/pictures/numbers, short visual demonstrations and reviewed spoken cues when language is useful. Text is secondary support, not the primary instruction channel.
6. **Child-facing UI words are presented in CAPITAL letters by default (ADR 0034).** Children learn capitals first. Localized strings comply automatically through `LocalizedResources.text()`; package-local literal strings must go through `greia_platform.child_text.display_text(...)`. Never hand-capitalize or leave child-facing literals mixed-case, and never case-transform child-authored content (for example Writing documents). A parent may choose normal text per child; the policy is presentation-only and must never feed gameplay, difficulty, permissions or stored data.
7. **Every new Activity must explicitly decide its child-facing presenter/character and speech plan.** Greia's recurring cast should normally be considered as social anchors, guides, reactions and curiosity hosts; omission must be deliberate, not accidental. When new prerecorded speech is produced, use the canonical Greia Voice Production Engine; Activity code/scripts must not implement their own Chatterbox/native-TTS/Whisper path.
8. **Subject-rich Activities must explicitly consider an optional researched curiosity/facts interaction.** When appropriate, use short, well-sourced, child-safe facts delivered through multilingual-ready semantic cues and reviewed localized speech.
9. **Every new Activity must explicitly consider child microphone/voice recording as an available Greia capability.** Voice recording is encouraged where it adds real creative, expressive, pre-reader or educational value. Ordinary voice capture should use the platform-owned `audio.basic` route and Greia's lightweight cleanup; do not avoid a good recording interaction merely because the reference hardware microphone is noisy. Omission remains valid when recording adds no value.
10. **Every new Activity must explicitly decide its score/progress/reward model.** Local score, durable Activity progress, completion/milestone events, personal-best score events, Greia Star eligibility, global achievement opportunities and optional achievement emblem art must each be deliberate decisions. Activities report facts; Greia owns global Stars, badges, trophies and achievement truth.
11. **A new or substantively changed Activity is not done until the final runtime-relevant source state passes the real Greia Simulator launch/survival gate.** Source validation, imports, unit tests, `make verify`, `python main.py`, or package validation do not replace this.
12. Simulator launch evidence becomes stale after any runtime-relevant edit. Relaunch the final state.
13. If the simulator cannot be run, report `INTEGRATION-UNVERIFIED` / `SOURCE-VERIFIED / SIMULATOR-UNVERIFIED`; do not call the Activity complete or working.
14. Claim only evidence that actually executed. Simulator evidence is not physical Acer/Pi evidence.

For child-facing pre-reader design, read:

```text
skills/greia-activity-authoring/PRE_READER_UX.md
```

For presenter/voice/fact design, read:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

For actual prerecorded speech production, read:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
```

For child microphone/voice-recording design or implementation, read:

```text
skills/greia-activity-authoring/MICROPHONE_RECORDING.md
```

For score/progress/Stars/badges/trophies, read:

```text
skills/greia-activity-authoring/ACHIEVEMENTS.md
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
skills/greia-activity-authoring/PRE_READER_UX.md
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
skills/greia-activity-authoring/MICROPHONE_RECORDING.md
skills/greia-activity-authoring/ACHIEVEMENTS.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
docs/architecture/GREIA_ACTIVITY_ECOSYSTEM.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
```

If actual new speech assets are produced during the task, additionally read and use:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
```

A new Activity design must record:

```text
pre-reader instruction strategy
lead presenter/mascot or deliberate none
speech/shared-utterance plan
whether optional curiosity facts fit the subject
microphone/voice-recording decision: included / considered-unnecessary / intentionally excluded
if recording is included: required-or-optional, child start/stop/replay flow, saved-data policy, fallback
supported locales / multilingual speech plan
local session score or deliberate none
durable Activity progress/save model or deliberate none
completion and milestone events
personal-best score event or deliberate none
Greia Star eligibility intent
global achievement opportunities or deliberate none
Activity achievement emblem plan or deliberate none
```

Do not treat text instructions, voice, presenter design, localization, microphone recording, progress, score or rewards as things to bolt on after gameplay is otherwise finished.

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

If the change affects child-facing instructions, controls, feedback, layout or completion, also read:

```text
skills/greia-activity-authoring/PRE_READER_UX.md
```

If it affects character presence, generated speech, knowledge/facts, localization or child-facing presentation, also read:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

If it actually produces new prerecorded speech, additionally use:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice.py
```

If it affects microphone capture, child voice recording, recording storage/replay or audio-input device handling, also read:

```text
skills/greia-activity-authoring/MICROPHONE_RECORDING.md
```

If it affects score, saved progress, completion/milestone/score events, Stars, badges, trophies or achievement art, also read:

```text
skills/greia-activity-authoring/ACHIEVEMENTS.md
```

### Refactoring or splitting an existing Activity

Read:

```text
skills/greia-activity-authoring/REFACTORING.md
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

The launch gate is mandatory after the **final** refactor edit. A clean architecture that fails in the Simulator is a failed refactor.

If the refactor changes child-visible flow or controls, rerun the pre-reader UX pass too.
If it changes microphone capture/recording ownership, rerun the `MICROPHONE_RECORDING.md` review too.
If it changes progress/event/reward semantics, rerun the `ACHIEVEMENTS.md` review too.
If it migrates voice-generation tooling, use `skills/greia-voice-production/SKILL.md`; do not preserve a parallel backend implementation merely because an old generator existed.

### Manifest, Collection, age/difficulty or discovery work

Read:

```text
skills/greia-activity-authoring/DISCOVERY.md
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
src/greia_platform/activities.py
src/greia_platform/activity_discovery.py
src/greia_launcher/catalogue_view.py
```

If manifest event declarations or achievement-art declarations are involved, also read `ACHIEVEMENTS.md`.
If `audio.basic` or other microphone capability declarations are involved, also read `MICROPHONE_RECORDING.md`.
If runtime-relevant manifest data changed, also run `LAUNCH_ACCEPTANCE.md`.

### UI, layout, canvas, responsive or input work

Read:

```text
skills/greia-activity-authoring/PRE_READER_UX.md
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

Runtime-relevant UI/input work must finish with `LAUNCH_ACCEPTANCE.md` and, when the child-facing flow changed, a no-reading UX pass from `PRE_READER_UX.md`.

### Victory, completion, results, Continue or Play Again work

Read:

```text
skills/greia-activity-authoring/PRE_READER_UX.md
skills/greia-activity-authoring/TERMINAL_RENDERING.md
skills/greia-activity-authoring/ACHIEVEMENTS.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

Exercise the completion/restart path, not just startup. Continue/Replay must be understandable without requiring the child to read the label. If completion should emit a semantic fact, verify that exact event path in the Simulator.

### Progress, score, Stars, badges, trophies, completion/milestone events or achievement art

Read:

```text
skills/greia-activity-authoring/ACHIEVEMENTS.md
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
runtime/progression-policy.toml
runtime/achievement-policy.toml
```

Core authority rule:

```text
Activity-local state/save     -> Activity + approved Greia storage
trusted history/best score    -> Greia event/history services
Greia Stars                   -> platform progression policy
global badges/trophies        -> platform achievement policy/presentation
```

A gold trophy is a visual presentation of a platform-owned gold-tier achievement; it is not something an Activity awards directly.

If event-emitting runtime code changed, run `LAUNCH_ACCEPTANCE.md` and exercise the actual event-producing path.

### Packaging, install or `.greiaactivity` work

Read:

```text
docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md
docs/adr/0033-fail-soft-activity-crossbindings-and-dev-noise-scrub.md
src/greia_platform/activity_package_format.py
src/greia_platform/activity_packages.py
src/greia_platform/activity_assets.py
src/greia_platform/activity_tree_cleanup.py
src/greia_platform/trust.py
```

Use the Simulator's canonical package-install path for package acceptance; then follow `LAUNCH_ACCEPTANCE.md`.

Development-machine metadata/cache contamination is not part of the Activity package contract and must not be “fixed” by weakening validation or adding package-local deletion logic. Installed Greia owns the narrow sanitation/recovery boundary defined by ADR 0033; genuine package defects remain genuine validation failures.

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
For actual new speech production, use `skills/greia-voice-production/SKILL.md`.
For microphone/voice-recording interactions also read `MICROPHONE_RECORDING.md`.
For badge/trophy child-facing copy or achievement art, also read `ACHIEVEMENTS.md`.

If visible/runtime resources changed, finish with `LAUNCH_ACCEPTANCE.md` in the materially affected locale/profile configuration.

### Character presenter, speech, pedagogical speech, facts or voice generation

Read:

```text
skills/greia-activity-authoring/PRE_READER_UX.md
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
skills/greia-voice-production/SKILL.md
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

For quick use/install instructions:

```text
tools/greia_voice_core/README.md
```

If the child also records or replays their own voice, add:

```text
skills/greia-activity-authoring/MICROPHONE_RECORDING.md
```

For actual production, use:

```text
tools/greia_voice.py
```

Only when installing/troubleshooting the authoring provider environment, read:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Only Voice Engine maintainers diagnosing Chatterbox internals should normally read:

```text
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

### Microphone/capture/child voice-recording work

Read **first**:

```text
skills/greia-activity-authoring/MICROPHONE_RECORDING.md
```

Then inspect exact authorities as needed:

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
src/greia_platform/audio.py
src/greia_platform/activity_api.py
```

For ordinary voice recording, use `audio.basic` and Greia's SDK route. The lightweight cleaned path is an available platform capability and should be used where recording genuinely improves the Activity.

Do not implement Activity-local device selection or DSP policy. Do not bypass the route to obtain raw ALSA input. If genuinely unprocessed signal is an accepted Activity requirement, the current platform needs a typed API/product extension; ordinary Activity code must not silently override the Parent-owned processing policy.

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
2. For new/child-facing work: did the no-reading UX pass succeed? Is any core instruction text-dependent?
3. For a new Activity: what presenter/speech/curiosity-fact decision was made?
4. If new prerecorded speech was produced: was it generated through the Greia Voice Production Engine and human-reviewed, rather than through an Activity-local backend path?
5. For a new Activity: was microphone/voice recording considered, and if included does it use audio.basic + the Greia SDK route?
6. For a new Activity: what score/progress/events/Stars/achievement decision was made?
7. Which source/test validation actually ran?
8. What exact final source SHA/state was launched through Greia Simulator?
9. Did it reach a usable frame, survive >=10s, survive meaningful input, exercise relevant completion/score/milestone/recording paths, and return cleanly to Shell?
```

If the Activity requires reading for its ordinary core instructions, the child-facing UX is failed even if the code launches and tests pass.

If #8 or #9 has no successful evidence, the correct status is **integration-unverified**, not complete.

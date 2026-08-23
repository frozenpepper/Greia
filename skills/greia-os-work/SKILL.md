---
name: greia-os-work
description: Canonical derived guide for substantive Greia OS/platform engineering, including architecture navigation, OOP/polymorphism, extension seams, low-resource performance, UI/input/display ownership, progression/achievements, audio, documentation, testing and evidence discipline.
---

# Greia OS Work Skill

**Status:** living derived OS/platform engineering guide  
**Audience:** coding agents, maintainers, contributors, reviewers  
**Reviewed:** 2026-08-24

This skill exists to make Greia OS work faster to start, harder to accidentally fragment, and easier for different contributors to continue consistently.

It is not a second architecture authority. Accepted ADRs own architecture decisions; source/runtime declarations own exact APIs, schemas and limits; product documents own accepted child-facing requirements. This skill is the practical map and implementation protocol that ties those authorities together.

---

## 1. Always read these before substantive OS work

Baseline read order:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/adr/0012-platform-architecture-constitution.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Before installing/configuring any toolchain, build host, simulator dependency, Parent checkout, developer-remote environment or voice backend, read:

```text
SETUP.md
```

Then read the narrower authority for the subsystem being changed.

Do not use chat history as the architecture source of truth.

---

## 2. Task-routing map

Read these additional authorities when relevant.

### Build/image/composition/install

```text
docs/adr/0013-image-composition-and-package-architecture.md   # inspect exact filename if ownership moved
docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
```

The exact accepted ADR/source owner wins if a filename above has moved; use `docs/DOCUMENTATION.md` to resolve it rather than creating another guide.

### Lightweight UI / Shell / collections

```text
docs/adr/0018-lightweight-ui-foundation.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

### Activity system navigation / trusted chrome

```text
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
```

### Input / controllers / pointer / touch

```text
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/testing/2026-08-15_PHASE0_INPUT_CONTROLLER_ACCEPTANCE.md
```

### Responsive display / viewport / canvas

```text
docs/adr/0026-resolution-adaptive-ui-layout.md
docs/adr/0027-activity-coordinate-spaces-canvas-and-world-camera.md
docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md
```

### Localization / language presentation

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
src/greia_platform/localization.py
src/greia_platform/language_presentation.py
```

### Progression / achievements / child Badge Library

```text
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
runtime/progression-policy.toml
runtime/achievement-policy.toml
src/greia_platform/history.py
src/greia_platform/achievements.py
src/greia_platform/achievement_art.py
src/greia_launcher/event_broker.py
src/greia_launcher/achievement_presentation.py
```

Activity-authored art is decorative only: platform policy explicitly admits bounded Activity emblems, while Greia retains achievement/reward authority, tier/frame, localization, profile state, visibility and celebration behavior.

### Activity Simulator

```text
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
```

### System updates

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

### Microphone capture / audio routing

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md
```

### Profile presentation / grammatical agreement

```text
docs/adr/0032-profile-presentation-and-grammatical-agreement.md
```

### Voice/speech asset production

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

### Activity implementation/package work

Also read:

```text
skills/greia-activity-authoring/SKILL.md
```

### Visual asset creation/integration

Also read:

```text
skills/greia-visual-authoring/SKILL.md
```

---

## 3. Greia architecture philosophy in one page

These principles should shape implementation before code is written.

### Linux is substrate, not the child product

Greia Shell is the child's OS surface. Do not expose a desktop environment, window manager, terminal, package manager, filesystem browser or generic Linux UI in the normal child path.

### Activity is the universal content abstraction

Python, Web and future runtimes are adapters below common Greia contracts for package identity, lifecycle, storage, profile context, permissions, input, progression/events and system chrome.

Do not let one runtime become the architecture definition.

### Authority belongs at the platform boundary

Platform-owned concerns stay platform-owned:

- profiles/session identity;
- trust/package validation;
- permissions;
- Home/Back system chrome;
- physical input/controller ownership;
- microphone route/processing policy;
- storage/history;
- global progression/reward/achievement truth;
- achievement localization/library/celebration behavior;
- install/update authority;
- hardware capability facts.

Activities may report factual events and may offer explicitly bounded decorative achievement emblems, but they do not gain writable global reward/achievement authority.

A library being technically capable of bypassing Greia is not permission to do so.

### Offline-first is default

Core child operation, Activities, saves, progression, language assets and Parent management must not require cloud services.

### Low-resource hardware is a correctness target

The first-generation Acer Aspire One remains the extreme floor. Modern developer hardware must not redefine acceptable CPU, RAM, rendering or storage behavior.

### ARM and legacy x86 are architecture peers

Do not bake architecture-specific semantics into portable state or platform contracts. Hardware/runtime variation belongs behind adapters.

### No architecture-by-simulator

The simulator composes real Greia services over synthetic absent-machine facts. It must never grow duplicate policy implementations merely because desktop testing is convenient.

### No convenience bypasses of trust or safety

Installer, sandbox, package trust, protected input and update boundaries remain fail-closed even when a developer path could be simpler.

---

## 4. Canonical module/layer ownership

Preserve this dependency direction:

```text
greia_platform
    stable platform contracts, services and shared primitives

        ↑ consumed by

greia_launcher
    child Shell/session orchestration and presentation

greia_parent
    Parent authority/API surface

greia_installer
    install UI + destructive operation boundary

greia_simulator
    development-only composition around real shared owners

activities/*
    supervised Activity implementations using public Greia APIs
```

Renderer/runtime/hardware-specific implementations belong below stable semantic interfaces.

When deciding where new code lives, ask:

1. Is this a portable Greia semantic contract? → usually `greia_platform`.
2. Is this child Shell/session orchestration/presentation? → `greia_launcher`.
3. Is this Parent authority/settings/API behavior? → `greia_parent`.
4. Is this destructive installation policy/engine? → `greia_installer`.
5. Is this only a desktop/synthetic composition fact? → `greia_simulator`, below shared policy seams.
6. Is this supervised child content? → an Activity, using public platform APIs.
7. Is this renderer/device-specific? → a concrete adapter below a typed platform seam.

Do not solve ownership uncertainty by creating a generic `common`, `utils`, `manager` or cross-layer singleton dump.

---

## 5. OOP: strong and pragmatic

Greia deliberately prefers a clean object-oriented architecture, but not abstraction for its own sake.

### 5.1 Model stable concepts with objects

Use classes/dataclasses when a concept owns:

- invariants;
- meaningful mutable state;
- lifecycle/cleanup;
- resource ownership;
- a coherent behavior family;
- a genuine substitution seam.

Good Greia examples include:

- runtime adapters;
- display/session backends;
- system-chrome backends/coordinators;
- input/HAL backends;
- storage/session objects;
- UI Screens/Overlays/Collections;
- package/update transactions;
- bounded cache owners;
- hardware/service adapters.

Use small pure functions for local math/transforms where an object would add no ownership.

### 5.2 Prefer composition over inheritance

Compose services/capabilities into the owner that uses them.

Inheritance is appropriate only when the subtype is genuinely substitutable for the base contract. Avoid deep inheritance stacks and mixin webs.

### 5.3 Use polymorphism at genuine variation points

When multiple implementations provide one semantic behavior, define one narrow typed Protocol/ABC and inject the implementation.

Canonical style:

```text
DisplaySessionBackend
  ├── current compatibility backend
  └── future accepted direct/session backend

AudioProcessingBackend
  ├── ALSA-backed implementation
  └── future backend behind same semantic service

RuntimeAdapter
  ├── Python runtime
  ├── simulator development composition where explicitly selected
  └── future canonical Web runtime
```

Repeated branch trees such as:

```python
if backend == "x11": ...
elif backend == "kms": ...
elif backend == "wayland": ...
```

spread across callers are a warning that a polymorphic seam may be missing.

A single local conditional is not automatically a reason to create a class hierarchy.

### 5.4 Keep interfaces narrow

A protocol should describe the smallest behavior callers need.

Do not create a universal system manager with display, input, audio, network, storage, update and lifecycle methods.

### 5.5 Dependencies are injected at architecture seams

Avoid mutable global service locators and hidden singleton state. Owners should receive the collaborators they depend on.

This makes:

- runtime/backend replacement explicit;
- simulator composition possible without policy duplication;
- unit tests simple;
- resource ownership visible.

---

## 6. Extension protocol: reuse first, then extend deliberately

Before creating a new service/helper/base class:

### Step 1 — Find the semantic owner

Read `docs/DOCUMENTATION.md`, architecture docs and relevant source. Identify which existing package/class owns the concept.

### Step 2 — Search existing primitives

Inspect nearby platform classes/protocols/helpers and tests. Reuse or extend the canonical owner instead of copying behavior into another subsystem.

### Step 3 — Name the variation

Write down what actually varies:

```text
semantic behavior that stays stable
vs
backend/runtime/hardware implementation that changes
```

If you cannot state that clearly, a new polymorphic interface is probably premature.

### Step 4 — Choose the smallest seam

Prefer:

- one narrow Protocol/ABC;
- one typed dataclass/value object;
- one cohesive service;
- composition through constructor injection.

Avoid broad frameworks and speculative future APIs.

### Step 5 — Put code in the correct layer

Portable semantics above; renderer/device/runtime mechanics below.

### Step 6 — Make ownership/lifecycle explicit

For long-lived resources, define:

- who creates it;
- maximum/bound;
- who may use it;
- reconnect/retry semantics where applicable;
- teardown/close behavior;
- failure fallback.

### Step 7 — Add contract tests

Test the interface semantics independently from one concrete backend when possible. Add concrete integration evidence at the narrowest environment that can prove it.

### Step 8 — Update the documentation owner

If the seam is intended for future contributors, document it in the relevant ADR/living architecture/engineering manual/skill in the same tranche.

Do not make future contributors infer a stable extension contract from one implementation file.

---

## 7. Source-file and entrypoint discipline

Large monoliths are a maintenance warning in OS code too.

Entrypoints should compose/launch systems rather than own every subsystem.

Review triggers, not automatic failures:

- a bootstrap/entrypoint above roughly **150–200 lines** should justify why composition is that complex;
- a module above roughly **500–700 lines** should be reviewed for multiple ownership reasons;
- a method above roughly **60–80 lines** should be reviewed for mixed policy, IO, rendering or lifecycle work;
- a class that owns unrelated domains should be split before more responsibilities are added.

Do not game these thresholds with arbitrary file splitting. Decompose by stable ownership.

Typical healthy split:

```text
semantic model / value objects
service or coordinator
narrow backend protocol
concrete backend implementation
presentation adapter
persistence/config adapter
tests for contract + implementation
```

Avoid `utils.py` becoming a landfill. A reusable helper should live near the semantic owner with a clear name and tests.

---

## 8. Performance protocol

The measured performance manual is mandatory for frame-loop, cache, rendering, pacing and resource work:

```text
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

### Core measured lessons

On the reference Acer software-rendered path:

- large per-pixel-alpha blends are extremely expensive;
- opaque full-screen copies are comparatively cheap;
- image decode and large `smoothscale` are too expensive for frame loops;
- generic/unconverted surfaces can force slow paths;
- full-scene rebuilds can turn a tiny hover change into visible stutter;
- unnecessary idle wakeups consume meaningful CPU.

### Mandatory engineering patterns

1. Measure the actual user-visible phase before optimizing.
2. Convert decoded display surfaces once at the correct cache boundary.
3. Precompose large static visuals into opaque reusable surfaces where appropriate.
4. Separate static scene identity from dynamic hover/animation state.
5. Incrementally repair/redraw only what changed where correctness allows.
6. Bound caches to the measured working set plus explicit memory limits.
7. Keep image decode/scale/font construction/filesystem IO/device enumeration/subprocess/config parsing/storage writes out of hot loops.
8. Render static UI on invalidation rather than continuously repainting unchanged pixels.
9. Make every cache's invalidation story explicit.
10. Keep optimized paths fail-soft with a correct fallback.
11. Prove rendering optimizations equivalent to the correct/naive path where practical.
12. Preserve input-latency budgets while reducing idle CPU.

### Do not optimize folklore

The repository already contains a precedent where assumed pacing behavior was wrong. Measure before changing architecture around a belief about SDL/Pygame/Linux behavior.

### Evidence scope

Desktop/headless timings can show relative regressions. They do not prove Acer/Pi performance.

Physical claims must name:

- machine;
- source SHA;
- measurement method;
- before/after phase;
- RSS sanity where relevant;
- visual/semantic correctness evidence.

---

## 9. UI architecture

Greia UI is intentionally lightweight:

```text
Screen
  -> optional Overlay/Sheet
  -> Panel/Card/Collection
  -> Control
```

Do not introduce a desktop/window-manager abstraction, draggable/resizable arbitrary windows, generic taskbar, broad retained scene graph, DOM clone or giant widget toolkit without an accepted architecture decision.

Use existing shared UI/layout primitives before creating local widgets.

Static Shell presentation should move toward invalidation-driven redraw. Animations should be bounded, purposeful and resource-aware.

A Collection is a semantic child grouping, not a filesystem folder.

---

## 10. Display/session and protected system chrome

Current production still uses a provisional Xorg/xinit compatibility backend while the direct/session architecture remains open.

Therefore:

- do not deepen X11 coupling in semantic layers;
- do not make Activities own DRM/display-session authority;
- do not use current Xorg behavior as the architectural API;
- preserve the Greia-owned Home/Back layer above Activity content;
- protected input must be intercepted before Activity delivery;
- a future compositor/session broker is justified only by evidence and Greia requirements, not desktop convention.

The stable semantic design should survive replacement of the current compatibility backend.

---

## 11. Input and controllers

Physical input ownership is a Greia platform concern.

Keep the chain conceptually:

```text
physical devices
  -> trusted Greia input backend
  -> reserved/protected system input interception
  -> runtime-neutral interaction mapping
  -> Activity semantic actions
```

Do not spread:

- SDL/raw button numbers;
- controller-brand strings;
- dead-zone constants;
- reconnect scanning;
- joystick indices;
- `/dev/input` access;
- global controller-to-Linux-mouse emulation

through Activities or launcher policy.

A pointer-emulating controller uses Greia semantic virtual-pointer behavior, not a global OS mouse hack.

Text Activities must preserve real text-key semantics.

---

## 12. Audio architecture

Greia has two distinct audio concerns that contributors must not mix.

### 12.1 Runtime microphone routing/processing

Architecture authority:

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
```

Core rule:

> Microphone capture routing and cleanup policy are platform-owned. Activities consume the selected route; they do not select Linux devices or implement their own denoising policy.

Current semantic owners include:

```text
src/greia_platform/audio.py
    AudioSettingsStore
    AudioService
    AudioProcessingBackend
    AlsaAudioProcessingBackend

src/greia_platform/activity_api.py
    get_audio_capture_device()
    get_audio_processing_mode()
```

The service deliberately separates desired Parent state, effective route, available endpoints and backend identity so stored preference is never mistaken for hardware truth.

Engineering rules:

- keep DSP implementations behind `AudioProcessingBackend` or the current exact semantic seam;
- never benchmark/promote a processor automatically as policy;
- lightweight processing is the desired default only when a real endpoint is available;
- advanced processing is explicit Parent opt-in and may legitimately be absent on Acer-class hardware;
- readiness markers represent current runtime truth and must not be persisted/faked;
- do not turn this narrow service into a desktop sound-server architecture without evidence.

### 12.2 Character/system/pedagogical speech assets

Voice generation is largely a build-time/content concern, governed by:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

Do not make OS runtime architecture depend on local voice-generation tooling.

Greia distinguishes character dialogue, shared character utterances, pedagogical speech and Dani system speech. The runtime should consume reviewed packaged/shared assets through semantic resource APIs, not generate mascot dialogue opportunistically on the child device.

---

## 13. Storage, progression, achievements and portable state

Child durable state must remain architecture-neutral and profile-scoped.

Activities write only through their Activity-owned Greia storage scope. They report factual events; platform history/progression/reward/achievement services own global interpretation.

Canonical progression split:

```text
Activity declared factual events
  -> trusted HistorySummary owns aggregates/personal bests
  -> runtime/progression-policy.toml owns repeatable Greia reward economics
  -> runtime/achievement-policy.toml + ProfileAchievementService own one-time milestones
  -> Greia Shell owns Badge Library / celebration presentation
```

Activities may optionally offer language-neutral decorative achievement emblems through the bounded `[achievement_art]` contract. Those declarations are not progress state and are inert unless the platform achievement policy explicitly admits them.

Do not duplicate storage/progression/history/achievement implementations in:

- launcher;
- simulator;
- Parent UI;
- individual Activities;
- runtime adapters.

Never let an Activity write global Star balances, `achievements.json`, global achievement definitions or unlock state.

Uninstall and child-data deletion remain separate semantics.

Keep histories, caches and queues explicitly bounded. Achievement presentation caches must include complete semantic/art identity and invalidate when admitted Activity artwork changes.

---

## 14. Package, trust, install and update boundaries

Package filenames/extensions are UX/routing hints, never trust evidence.

Validation/trust must remain based on the canonical Greia package/parser/service contracts.

Removable media is untrusted and never autoruns executable Activity code.

Whole-disk installation remains graphical and fail-closed; target/payload identity must be revalidated before destructive operations.

System updates are platform-owned transactional artifacts. Current single-root profiles must not acquire an unsafe in-place active-root fallback merely to make updates easier.

Do not expose package managers, arbitrary shell commands or privileged mutation APIs to Activities.

Optional Activity achievement artwork is content, not trust evidence. Parent-installed Activity art must never auto-register global achievements merely because the package is valid or installed.

---

## 15. Simulator rule: vary facts, not Greia policy

The Activity Simulator is a high-value architecture test because it should compose the same Greia services over synthetic hardware facts.

If simulator work needs to reimplement:

- manifest parsing;
- permissions;
- profiles;
- storage;
- progression/history/achievement evaluation;
- achievement-art admission;
- launcher catalogue;
- localization;
- responsive transforms;
- future Web semantics;

stop and move the seam to the shared owner instead.

Simulator-specific code belongs at genuine absent-machine variation points such as synthetic HAL facts, isolated development roots or a runtime/display adapter selected by the simulator architecture.

Never branch Activity/platform semantics on `GREIA_SIMULATOR` merely to make a test pass.

---

## 16. Resource and lifecycle ownership

Every long-lived resource must have a named owner and cleanup path:

- subprocess;
- thread/worker;
- queue;
- display/session lease;
- system-chrome lease;
- controller handle;
- mount;
- network listener;
- cache;
- renderer surface pool;
- temporary directory;
- update/install transaction;
- audio processing endpoint.

Document or encode:

- maximum count/size;
- acquisition;
- normal close;
- failure close;
- stale/reconnect behavior where relevant.

A hidden resource that merely dies when the process exits is usually not an adequate lifecycle design.

---

## 17. Commenting and docstrings

Good Greia comments preserve design intent.

Public architectural classes, protocols and extension points should document:

- what they own;
- lifecycle;
- important invariants;
- allowed dependency direction;
- resource bounds;
- failure/fallback semantics where non-obvious.

Non-obvious algorithms need comments explaining **why**, particularly for:

- cache keys/invalidation;
- dirty-region geometry;
- security/trust checks;
- race/lifecycle handling;
- hardware workarounds;
- performance tuning derived from measurement;
- compatibility behavior that must disappear with a future backend.

Do not comment obvious syntax.

Do not leave unexplained magic constants from hardware tuning. Name them and point to the measurement/protocol/reason.

A stable contributor-facing extension seam belongs in docs as well as code.

---

## 18. Documentation maintenance protocol

Documentation is part of the implementation contract.

After substantive work, update the document that owns the changed fact rather than dumping everything into `HANDOVER.md`.

Typical updates:

```text
architecture decision changed
  -> accepted/new ADR + architecture synthesis as required

exact implementation contract changed
  -> source/tests; derived docs that quote it must follow

repository-wide engineering rule changed
  -> docs/engineering/ENGINEERING_FOUNDATIONS.md

measured performance lesson changed
  -> docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md

Activity author-facing contract changed
  -> skills/greia-activity-authoring/*

OS/platform contributor workflow changed
  -> this skill and/or docs/agents/GREIA_AGENT_OPERATIONS.md

achievement/reward authority or Badge Library contract changed
  -> GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY + relevant Activity/OS skills

visual system changed
  -> GREIA_ART_GRAPHICS_SYSTEM + visual skill/current visual workstream docs

current continuation/evidence changed
  -> HANDOVER.md
```

Preserve append-only historical evidence/progress where the repository says history is append-only. Do not rewrite old failures away.

---

## 19. Testing and evidence ladder

Test at the narrowest layer that can prove the claim.

### Pure/source tests

Best for:

- value objects/state machines;
- parser/serialization/validation;
- protocol dispatch;
- lifecycle/cleanup;
- cache bounds/invalidation;
- layout math;
- input normalization;
- rollback/failure invariants.

### Simulator

Best for real Greia semantic integration over synthetic hardware facts.

Does not prove physical/back-end behavior.

### VM/image

Best for image composition, boot, installer, package footprint and virtual backend facts.

Does not automatically prove physical reference hardware.

### Physical hardware

Required for claims about actual Acer/Pi CPU/RAM/display/input/audio/network/device behavior.

Always classify evidence honestly and record the exact source SHA.

Do not query/run GitHub Actions as an execution/evidence service without explicit owner authorization.

---

## 20. Start-of-change protocol

For substantive OS work:

1. refresh current `main` and read current `HANDOVER.md`;
2. identify the exact semantic owner and relevant ADR/source;
3. classify the work layer and evidence needed;
4. inspect existing abstractions before designing a new one;
5. state the invariant/variation/lifecycle/resource bound before implementing a new service or protocol;
6. implement the smallest cohesive change;
7. add focused contract tests first where practical;
8. measure before/after for performance-sensitive work;
9. run the verification appropriate to the touched subsystem;
10. update owning docs/skills/handover as required;
11. commit coherent work to canonical `main` unless the owner explicitly asked for another branch workflow.

For code changes, run the repository's required verification from current instructions before claiming a green state. Do not claim a test you did not execute.

---

## 21. OS engineering review gate

Before calling a substantive platform change complete, ask:

1. Is the behavior in the correct package/layer?
2. Is there an existing owner/abstraction that should be extended instead?
3. Is a new class modeling real state/invariants/lifecycle/ownership?
4. Is a new Protocol/ABC justified by genuine substitutable implementations?
5. Is composition preferred over deep inheritance?
6. Are dependencies injected and visible?
7. Are runtime/hardware-specific details below stable semantic contracts?
8. Are resources/caches/queues/histories/device sets bounded?
9. Is cleanup/reconnect/failure ownership explicit?
10. Is hot-path code free of image decode/scale, blocking IO, device discovery, subprocess calls, config parsing and durable writes?
11. Does every cache have a complete key and invalidation story?
12. Does performance work have before/after evidence and correctness proof?
13. Does the change preserve the Acer floor and architecture neutrality?
14. Does it preserve protected Home/Back and input authority?
15. Does it preserve platform-owned microphone routing and Parent policy?
16. Does it preserve platform-owned progression/reward/achievement authority while keeping optional Activity art decorative and explicitly admitted?
17. Does the simulator still consume shared Greia policy rather than clone it?
18. Is a monolithic file/class growing where responsibilities should be split?
19. Are public extension points documented with ownership/lifecycle/invariants?
20. Were the correct owning docs/skill/handover updated?
21. Is the evidence scope stated honestly?

---

## 22. Common anti-patterns to reject

- giant cross-domain `Manager` or `Application` god objects;
- entrypoints that contain the entire OS subsystem;
- deep inheritance/mixin webs;
- speculative generic frameworks;
- backend/runtime/device string conditionals copied across callers;
- mutable global service locators;
- duplicate platform services inside launcher/simulator/Activities;
- X11/SDL/ALSA details leaking into portable product semantics;
- unbounded caches/queues/history/device registries;
- per-frame image decode/scale/font creation/filesystem IO/device enumeration/subprocess/config parsing;
- Activity-drawn trusted Home/Back;
- Activity-local global Star/achievement mutation or an `award_badge()` bypass;
- automatically importing global Badge Library definitions merely because an Activity declares art/content;
- embedding localized child-facing words in Activity badge emblem images;
- raw `/dev/input` grants to solve controller support;
- Activity-local microphone device selection/denoising;
- fake readiness markers or stored preference presented as hardware truth;
- simulator-only semantic behavior branches;
- arbitrary shell command construction at privileged boundaries;
- comments that narrate syntax while architectural `why` remains undocumented;
- magic hardware-tuning constants with no measurement provenance;
- documentation that contradicts the current source owner.

The Greia standard is: **small strong abstractions, explicit ownership, purposeful polymorphism, reusable platform services, measured low-resource behavior and documentation that keeps the next contributor out of archaeology.**
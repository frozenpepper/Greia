# Greia Activity Engineering and Performance

**Status:** mandatory derived Activity implementation guidance  
**Audience:** Activity authors, coding agents, reviewers  
**Reviewed:** 2026-08-23

This companion translates Greia's repository-wide engineering and measured-performance rules into a practical Activity-development protocol.

Authority remains, in order, with accepted ADRs and exact source/runtime declarations. The two primary engineering authorities behind this guide are:

```text
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

This file does not create a second Activity API. Before naming or extending a Greia class, protocol or helper, inspect the current source owner and use the implemented API.

---

## 1. The standard

A Greia Activity should be easy for another contributor to understand, profile, test and extend without reading a giant entrypoint or reconstructing hidden architecture.

The target is not maximal abstraction. The target is:

- small cohesive modules;
- explicit state and ownership;
- strong OOP where a stable concept actually owns behavior/invariants;
- purposeful polymorphism at genuine variation points;
- composition instead of deep inheritance;
- reuse of Greia platform services and shared primitives;
- bounded resource use on the Acer-class floor;
- rendering/input loops with no accidental heavyweight work;
- comments/docstrings that explain ownership, invariants and non-obvious decisions;
- tests around semantic behavior and performance-sensitive equivalence.

A feature is not complete merely because it works on a modern development machine.

---

## 2. `main.py` is a composition root, not the Activity

For new first-party Activities and substantive rewrites, `main.py` MUST remain a thin bootstrap/composition boundary.

It may reasonably:

1. obtain the Greia/runtime context;
2. construct shared resources/adapters/services;
3. construct the Activity/application object;
4. enter its run/lifecycle method;
5. translate an unrecoverable top-level failure into the expected Activity exit/lifecycle behavior.

It should NOT own:

- game rules;
- round generation;
- scoring/progression semantics;
- widget/layout implementations;
- scene rendering details;
- asset decoding/scaling policy;
- audio sequencing policy;
- storage schema/business logic;
- controller/device mapping;
- large event-dispatch trees;
- localization tables;
- hundreds of constants for unrelated subsystems.

A several-hundred/thousand-line `main.py` is an architecture defect even when it works.

### Review thresholds, not line-count games

These are decomposition triggers, not automatic build failures:

- `main.py` above roughly **150 lines**: explain why bootstrap needs that size or split it;
- `main.py` above **250 lines**: normally reject for first-party code until responsibilities are extracted;
- any implementation module above roughly **500 lines**: review whether it owns more than one reason to change;
- a method above roughly **60–80 lines**: review for mixed state transition, IO, rendering or policy concerns.

Do not evade these thresholds by creating meaningless tiny files. Split by ownership and reason-to-change.

---

## 3. Recommended Activity shape

There is no mandatory filename taxonomy, but a non-trivial Python Activity should normally resemble this responsibility split:

```text
activities/my_activity/
├── activity.toml
├── main.py                 # composition/bootstrap only
├── app.py                  # Activity lifecycle / top-level state machine
├── model.py                # domain state and invariants
├── rounds.py               # challenge/round generation where applicable
├── presentation.py         # renderer/view composition
├── input.py                # semantic Activity actions, not physical devices
├── resources.py            # Activity-owned asset/resource preparation
├── audio.py                # Activity audio sequencing where genuinely needed
├── persistence.py          # Activity-owned profile state mapping where needed
├── locales/
└── assets/
```

Small Activities may combine several of these responsibilities. The rule is cohesion, not file multiplication.

Good examples of things worth modeling as classes/dataclasses:

- an Activity lifecycle/state machine;
- round/challenge state with invariants;
- a scene/presentation object that owns cached presentation resources;
- an audio sequencer that owns non-overlap/cancellation state;
- an Activity-specific repository over the Greia storage API when persistence is non-trivial;
- a generator/strategy when multiple challenge-generation behaviors are genuinely substitutable;
- a bounded asset/cache owner with an explicit invalidation lifecycle.

Keep tiny calculations and transformations as pure functions when an object would add no ownership or substitutability.

---

## 4. OOP and polymorphism protocol

### 4.1 Model ownership, not nouns

Create a class when the concept owns one or more of:

- invariants;
- mutable state;
- lifecycle/cleanup;
- a bounded resource;
- a coherent behavior family;
- a real substitution seam.

Do not create `SomethingManager` merely because several functions need a namespace.

### 4.2 Prefer composition

An Activity application typically composes domain state, renderer/presentation, semantic input handling, audio and persistence collaborators.

Prefer:

```text
ActivityApp
  has RoundModel
  has Presentation
  has AudioSequencer
  has PersistencePort
```

over a deep inheritance tree such as:

```text
BaseActivity -> AnimatedActivity -> AudioActivity -> GameActivity -> MyActivity
```

Inheritance is appropriate only when callers can genuinely substitute the subtype for the base contract without knowing which subtype they received.

### 4.3 Use polymorphism only at real variation points

A narrow Protocol/ABC is useful when callers need one semantic behavior with multiple implementations, for example:

```text
ChallengeGenerator
  ├── CountingChallengeGenerator
  └── ShapeChallengeGenerator

ActivityClock
  ├── MonotonicActivityClock
  └── FrozenTestClock
```

Do not invent an interface for every class. A single concrete implementation with no meaningful substitution need not have an ABC merely for style.

If repeated branches appear across the Activity like:

```text
if mode == ...
elif mode == ...
elif mode == ...
```

ask whether the branches represent a genuine strategy/state object. If they are just a small local state transition, an explicit enum/state machine may be clearer than polymorphism.

### 4.4 Dependencies are explicit

Inject collaborators into the object that owns them. Avoid mutable global singletons for renderer state, random generators, storage clients, clocks, audio state or caches.

Test seams should usually be the same seams production code uses, not special `if testing:` branches.

---

## 5. Reuse Greia before writing Activity-local infrastructure

Before adding a helper/framework/service, inspect the canonical platform owners.

Common shared areas include:

```text
src/greia_platform/activity_api.py
src/greia_platform/activity_ui.py
src/greia_platform/pygame_ui.py
src/greia_platform/pygame_canvas.py
src/greia_platform/responsive_layout.py
src/greia_platform/activity_viewport.py
src/greia_platform/input_core.py
src/greia_platform/localization.py
src/greia_platform/typography.py
src/greia_platform/emoji_palette.py
src/greia_platform/pygame_visual_assets.py
```

Performance-oriented shared patterns currently include `BoundedCache`, shared motion/effect primitives and `PygameVisualSurfaceCache`; inspect current source for the exact import/API before use.

Do NOT build Activity-local replacements for:

- Greia storage/profile scoping;
- progression/reward authority;
- system Home/Back;
- physical controller ownership/dead zones/mappings;
- microphone device selection/denoising policy;
- localization authority;
- package/trust validation;
- responsive viewport/platform-safe geometry;
- shared font/emoji fallback;
- system update/install behavior.

If several Activities need the same general helper and the behavior is platform-neutral, propose/extract it into the appropriate shared Greia layer with tests/documentation rather than copy/pasting it into Activity folders.

---

## 6. Performance is an Activity correctness contract

Greia's extreme reference floor is approximately a first-generation Acer Aspire One class machine: ~1 GHz single-core Atom, software-rendered Pygame/SDL, 1024×600 and <=1 GiB RAM.

The current measured manual establishes several important facts:

- large per-pixel-alpha blends can dominate a frame;
- opaque full-screen copies are comparatively cheap;
- `smoothscale` and image decode are far too expensive for hot loops;
- idle wake frequency has a measurable CPU cost;
- cached steady frames can already be very cheap if dynamic changes do not force a full rebuild.

Treat these as design inputs, not as a cleanup checklist after the Activity is finished.

### 6.1 Forbidden in a normal frame/event hot path

Do not repeatedly:

- `pygame.image.load()` or equivalent decode;
- `smoothscale`/large scale operations;
- construct fonts;
- render stable text that could be cached;
- allocate large Surfaces/overlays for unchanged content;
- generate static gradients/patterns/scenery;
- flip/transform sprites when the transformed state is reusable;
- perform filesystem walks/stat storms/package scans;
- enumerate devices/controllers;
- launch subprocesses;
- parse configuration files;
- write durable storage/autosaves.

If a frame needs any of those, move the work to load/preparation, a bounded cache miss, a state transition, a throttled/background owner, or an idle/level boundary as appropriate.

### 6.2 Cache correctly, not infinitely

Every cache needs:

- a clear owner;
- an explicit bound or demonstrated natural bound;
- a key containing every fact that changes its pixels/value;
- an invalidation/re-key story for resize, locale, theme/resource revision or Activity state as applicable;
- a graceful slow/correct fallback when the fast path cannot be used.

A cache without invalidation is a stale-state bug. A cache smaller than its measured working set can be a performance regression. An unbounded cache is not acceptable on Greia.

### 6.3 Bake static presentation

If scenery cannot change during a scene/round, render it once.

Prefer:

```text
static backdrop -> one reusable opaque surface
small changing objects -> redraw only when needed
transient alpha FX -> small bounded areas
```

over rebuilding a large RGBA scene because one pointer/character changed.

For sprites with reusable transforms, cache by semantic transform state such as:

```text
(asset_id, width, height, facing_or_state)
```

rather than scaling/flipping every frame.

### 6.4 Dirty/invalidation rendering

Static or turn-based Activities should not burn a continuous redraw loop while nothing is changing.

Maintain explicit invalidation/dirty state. Redraw when:

- input changes visible state;
- a bounded animation is active;
- an async result changes presentation;
- a timed semantic event genuinely requires it;
- the viewport/resource context changed.

When idle/static, wait/sleep at a cadence that preserves input responsiveness instead of repainting unchanged pixels.

### 6.5 Animation rules

Animations should be:

- sampled from monotonic time;
- math/state driven rather than frame-count dependent;
- bounded in duration/amplitude;
- allocation-light in the hot path;
- quantized/cached where visual equivalence permits;
- guaranteed to settle exactly to a neutral/end state.

Do not introduce a heavyweight retained animation framework for a few hover/bounce effects.

### 6.6 Working targets

Current Activity-facing performance targets are:

```text
smooth gameplay target: ~30 fps on Atom-class floor
added input latency:     <= 50 ms
static/paused idle CPU:  near zero where architecture permits
```

These are engineering targets, not proof obtained from a desktop. Hardware claims require named physical evidence.

---

## 7. Correctness comes before the fast path

A performance optimization must preserve semantic and visual behavior.

For cache/dirty-region/repair optimizations:

1. keep a simple correct path or an equivalent oracle where practical;
2. make the fast path an accelerator, not the sole correctness implementation;
3. test optimized output against the naive/full path under identical inputs;
4. freeze time/randomness when required for deterministic comparison;
5. include boundary states such as hover enter/exit, resize, locale change, round reset and animation completion.

Pixel-equivalence or targeted image-region equivalence is strongly preferred for rendering optimizations where practical.

Game rules need independent contract tests so a visual optimization cannot silently change scoring, collision, completion or progression events.

---

## 8. Audio engineering boundaries

Speech policy is defined by `VOICE_GENERATION.md`; microphone architecture is platform-owned.

Activity code must keep audio responsibilities narrow:

- request/use semantic audio cues rather than hard-coded host filenames where Greia resources own them;
- use shared character utterance families before duplicating generic praise/retry clips;
- use deterministic/system speech when the sound itself is educational truth;
- never enumerate/select microphone hardware or implement per-Activity denoising;
- obtain capture routing from `get_audio_capture_device()` when microphone access is granted;
- keep audio sequencing/cancellation state in one explicit owner when an Activity can overlap cues.

Loading/decoding a sound on every playback is the audio equivalent of loading an image every frame. Prepare/cache bounded reusable playback resources according to the runtime's supported pattern.

---

## 9. Commenting and docstring standard

Comments are required where they preserve architectural intent, not where they narrate syntax.

Public Activity-specific extension classes/protocols and non-obvious state owners should document:

- responsibility;
- ownership/lifecycle;
- important invariants;
- dependencies;
- resource bounds where relevant;
- why a non-obvious performance/correctness choice exists.

Good comment:

```text
# Restore from the precomposited backdrop before drawing the lifted card;
# clearing to a flat color would corrupt wallpaper pixels around the tile.
```

Bad comment:

```text
# Increment x by one.
x += 1
```

Do not leave unexplained magic timing/cache-size constants. Name them and link the measurement/product reason when it is not obvious.

If an Activity establishes a reusable pattern other Activities should follow, update this skill or the appropriate shared engineering/design document rather than relying on comments in one package.

---

## 10. Testing protocol for Activity implementation

At minimum, test the narrowest useful contracts for:

- domain/state transitions;
- round/challenge generation invariants;
- scoring/completion event emission;
- persistence serialization/migration when present;
- responsive/layout calculations where custom logic exists;
- semantic input behavior without binding tests to controller brands;
- cache bounds/invalidation;
- animation settle/end behavior;
- audio sequencing state where non-trivial;
- optimized renderer equivalence for performance-sensitive paths.

Then use the real Greia Activity Simulator for integration facts it can establish.

Do not claim the simulator proves Acer/Pi performance, physical controller behavior, trusted system chrome, real microphone quality or production display/session architecture.

For performance work, report before/after measurements for the actual interaction being improved. Physical performance claims must identify the machine and exact source SHA.

---

## 11. Activity engineering review gate

Before calling substantive Activity work complete, ask:

1. Is `main.py` still only bootstrap/composition?
2. Does each module/class have one coherent ownership reason?
3. Is there already a Greia platform primitive/service that should own any new helper?
4. Are classes modeling state/lifecycle/invariants rather than being decorative wrappers?
5. Are genuine variation points polymorphic instead of repeated type/mode conditionals?
6. Is composition preferred over deep inheritance?
7. Are dependencies explicit and testable?
8. Are long-lived resources and caches bounded and cleaned up?
9. Is image/font/text/scale/IO/device/storage work absent from hot loops?
10. Does static presentation render only on invalidation where practical?
11. Does every cache have a complete key and invalidation story?
12. Does a rendering fast path fail back to a correct path?
13. Are gameplay semantics covered independently from presentation optimizations?
14. Are comments/docstrings explaining ownership, invariants and non-obvious `why` decisions?
15. Could a new contributor find the correct extension point without reading a monolithic file?
16. Does the Activity still obey platform ownership of Home/Back, input devices, microphone routing, storage, progression, localization and trust?
17. Were performance claims measured at the scope actually claimed?

If several answers are no, refactor before adding more features.

---

## 12. What not to do

Reject these patterns in new/substantively changed first-party Activities:

- 1,000+ line `main.py` applications;
- giant `Game`/`Manager` classes owning model + rendering + audio + storage + input;
- one event loop containing gameplay policy, image loads, font rendering and persistence writes;
- Activity-local copies of Greia storage/input/audio/localization/platform services;
- unbounded dicts used as caches;
- per-frame filesystem/device/subprocess/config work;
- per-frame image decode/scale/flip/static gradient generation;
- deep `BaseGame -> ... -> MyGame` inheritance stacks;
- interfaces invented for every concrete helper with no substitution need;
- device/model/simulator checks scattered through Activity semantics;
- performance fixes that change pixels/gameplay with no equivalence/contract proof;
- undocumented magic constants whose values came from hardware tuning.

The intended result is simple code with strong seams—not enterprise ceremony.
# Greia Activity Engineering and Performance

**Status:** mandatory derived Activity implementation guidance  
**Audience:** Activity authors, coding agents, reviewers  
**Reviewed:** 2026-10-30

This companion translates Greia's repository-wide engineering, runtime and measured-performance rules into a practical Activity-development protocol.

Authority remains, in order, with accepted ADRs and exact source/runtime declarations. Primary engineering authorities:

```text
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
runtime/child-runtime.toml
src/greia_launcher/runtime_adapter.py
```

This file does not create a second Activity API or runtime policy. Before naming or extending a Greia class, protocol or helper, inspect the current source owner and use the implemented contract.

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
- module decomposition that the **real Greia runtime and repository tooling actually support**;
- bounded resource use on the Acer-class floor;
- rendering/input loops with no accidental heavyweight work;
- comments/docstrings that explain ownership, invariants and non-obvious decisions;
- tests around semantic behavior, runtime contracts and performance-sensitive equivalence.

A feature is not complete merely because it looks architecturally clean or works when launched directly on a developer machine.

---

## 2. `main.py` is a composition root, not the Activity

For new first-party Activities and substantive rewrites, `main.py` should remain a thin bootstrap/composition boundary.

It may reasonably:

1. obtain Greia/runtime context;
2. construct shared resources/adapters/services;
3. construct the Activity/application object;
4. retain a small compatibility export surface when established repository consumers require it;
5. enter the Activity lifecycle;
6. perform top-level cleanup.

It should not own:

- game rules;
- round generation;
- scoring/progression semantics;
- large widget/layout implementations;
- scene rendering details;
- asset decoding/scaling policy;
- audio sequencing policy;
- storage schema/business logic;
- controller/device mapping;
- large event-dispatch trees;
- localization tables;
- unrelated subsystem constants.

A several-hundred/thousand-line `main.py` is an architecture defect even when it works.

### Review thresholds, not line-count games

These are decomposition triggers, not automatic build failures:

- `main.py` above roughly **150 lines**: explain why bootstrap needs that size or split it;
- `main.py` above **250 lines**: normally reject for first-party code until responsibilities are extracted;
- an implementation module above roughly **500 lines**: review whether it owns more than one reason to change;
- a method above roughly **60–80 lines**: review for mixed state transition, IO, rendering or policy concerns.

Do not evade these thresholds by creating meaningless tiny files. Split by ownership and reason-to-change.

### Critical qualification: decomposition must be launchable

The thin-entrypoint rule does **not** authorize authors to assume Python's ordinary import environment is Greia's entire runtime contract.

When code moves into sibling modules, the Activity must still satisfy:

```text
Greia PythonRuntimeAdapter validation
runtime/script import semantics
repository/package import semantics
READY/STOP lifecycle verification
existing legitimate import/export consumers
project validation
actual Simulator/launcher startup
```

If any of those fail, the modularization is incomplete even if the OOP structure is better.

---

## 3. Recommended Activity shape

There is no mandatory filename taxonomy, but a non-trivial Python Activity should normally resemble this responsibility split:

```text
activities/my_activity/
├── activity.toml
├── main.py                 # composition/bootstrap + narrow compatibility only
├── app.py                  # Activity lifecycle / top-level state machine
├── model.py                # domain state and invariants
├── rounds.py               # challenge/round generation where applicable
├── presentation.py         # renderer/view composition
├── input.py                # semantic Activity actions, not physical devices
├── resources.py            # Activity-owned resource preparation
├── audio.py                # Activity audio sequencing where genuinely needed
├── persistence.py          # Activity-owned state mapping where needed
├── locales/
└── assets/
```

Small Activities may combine several responsibilities. The rule is cohesion, not file multiplication.

Good object candidates include:

- an Activity lifecycle/state machine;
- round/challenge state with invariants;
- a scene/presentation owner with cached prepared resources;
- an audio sequencer with non-overlap/cancellation state;
- an Activity-specific repository over Greia storage when persistence is non-trivial;
- a generator/strategy when multiple challenge-generation behaviors are genuinely substitutable;
- a bounded asset/cache owner with explicit invalidation lifecycle.

Keep tiny calculations and stateless drawing/transformation helpers as functions when an object would add no ownership or substitutability.

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

Prefer:

```text
ActivityApp
  has DomainModel
  has Presentation
  has AudioSequencer
  has PersistencePort
```

over:

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

If repeated mode branches appear, ask whether they represent a genuine strategy/state object. A small local transition may be clearer as an enum/state machine.

### 4.4 Dependencies are explicit

Inject collaborators into the object that owns them. Avoid mutable global singletons for renderer state, randomness, storage, clocks, audio state or caches.

Test seams should normally be the same seams production uses, not `if testing:` branches.

### 4.5 Do not promote abstractions after one example

An Activity-local abstraction becomes a platform candidate only after the same **semantics** recur across multiple Activities.

Before moving something into `greia_platform`:

1. compare at least one or two additional Activities;
2. identify the stable semantic contract;
3. ensure the platform really owns that responsibility;
4. provide a narrow API and tests;
5. migrate consumers deliberately.

Shared-looking filenames alone are not evidence of a reusable abstraction.

---

## 5. Python module and runtime compatibility

This section is mandatory for modular Python Activities.

### 5.1 Greia validates every Activity Python source

`PythonRuntimeAdapter` parses Activity Python files and enforces the curated runtime policy from `runtime/child-runtime.toml`.

The intended security distinction is:

```text
forbidden external/import root
    reject

package-local module or package inside manifest.root
    Activity code; allow

curated external import root
    allow

unknown external import root
    reject
```

Package decomposition must **not** require adding Activity-specific module names to the global `allowed_import_roots` list.

Forbidden imports remain forbidden even when decomposition is convenient. Platform anti-shadowing rules must also remain intact so an Activity cannot replace a curated module with a local lookalike.

### 5.2 Support both legitimate import contexts

Greia runs the manifest entrypoint as a script from the Activity root, while repository tests/tools may import it through `activities.<name>...`.

A modular Activity must work in both contexts.

Preferred pattern for new code:

```python
if __package__:
    from .model import ActivityModel
    from .presentation import ActivityPresentation
else:
    from model import ActivityModel
    from presentation import ActivityPresentation
```

A verified `try`/relative-import fallback may be retained where already established, but broad `except ImportError` can mask an ImportError raised *inside* the imported module. Avoid using broad exception handling as the default architecture.

Do not scatter `sys.path` manipulation through Activities.

### 5.3 Public compatibility exports matter

Before moving/renaming symbols, search repository tests and tools for imports from the old module.

If legitimate consumers exist, either:

- keep a small compatibility alias/export at the old location; or
- migrate all consumers coherently in the same tranche.

A thin `main.py` may therefore contain a few compatibility aliases. That does not make it a monolith.

### 5.4 Lifecycle ownership may move, semantics may not

`mark_activity_ready()` should live where the Activity knows the first usable frame has been presented. That may be in `app.py` rather than `main.py`.

The contract is semantic:

```text
present first usable frame -> publish READY exactly once
```

Repository verification must not accidentally freeze the old file layout. Likewise the Activity must prove the real launch path reaches READY.

---

## 6. Reuse Greia before writing Activity-local infrastructure

Inspect shared owners before adding a helper/framework/service:

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

Performance-oriented shared patterns include bounded caches and shared visual/motion primitives; inspect current source for exact APIs before use.

Do not build Activity-local replacements for:

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

---

## 7. Performance is an Activity correctness contract

Greia's extreme reference floor is approximately a first-generation Acer Aspire One: ~1 GHz single-core Atom, software-rendered Pygame/SDL, 1024×600, <=1 GiB RAM.

Measured platform work has established that:

- large per-pixel-alpha blends can dominate a frame;
- opaque full-screen copies are comparatively cheap;
- `smoothscale` and image decode are too expensive for hot loops;
- idle wake frequency has measurable CPU cost;
- cached steady frames can be cheap if small dynamics do not force full reconstruction.

Treat these as design inputs, not cleanup tasks after the Activity is finished.

### 7.1 Forbidden in a normal hot path

Do not repeatedly:

- `pygame.image.load()` or equivalent decode;
- `smoothscale` or other large reusable transforms;
- construct fonts;
- render stable text that can be cached;
- allocate large unchanged Surfaces/overlays;
- regenerate static gradients/patterns/scenery;
- flip/transform sprites when reusable;
- walk/stat package filesystems;
- enumerate devices/controllers;
- launch subprocesses;
- parse configuration;
- write durable storage/autosaves.

Move such work to preparation, a bounded cache miss, a semantic state transition, a throttled/background owner, or an appropriate level/idle boundary.

### 7.2 Cache correctly, not infinitely

Every cache needs:

- a clear owner;
- an explicit bound or demonstrated natural bound;
- a key containing every fact that changes its result;
- invalidation/re-key behavior for resize, locale, theme/resource revision or state as applicable;
- a correct fallback when the fast path cannot be used.

A cache without invalidation is a stale-state bug. An unbounded cache is unacceptable on Greia.

### 7.3 Bake static presentation

Prefer:

```text
static scene -> reusable opaque backdrop
small changing objects -> redraw as needed
transient alpha FX -> small bounded areas
```

over rebuilding a large RGBA scene because one object changed.

Cache reusable transforms by semantic transform state rather than scaling/flipping every frame.

### 7.4 Dirty/invalidation rendering

Static or turn-based Activities should not repaint continuously while nothing changes.

Redraw when:

- input changes visible state;
- a bounded animation is active;
- an async result changes presentation;
- a genuine timed semantic event requires it;
- viewport/resource context changed.

When static, retain input/stop responsiveness without repainting unchanged pixels unnecessarily.

### 7.5 Animation rules

Animations should be:

- sampled from monotonic time;
- math/state-driven rather than frame-count-dependent;
- bounded in duration/amplitude;
- allocation-light;
- quantized/cached where visually safe;
- guaranteed to settle to a neutral/end state.

Do not introduce a heavyweight animation framework for a few simple effects.

### 7.6 Working targets

```text
smooth gameplay target: 24 fps cap on the reference floor (FramePolicy.reference_floor); <=40 ms frame work
added input latency:     <= 50 ms
static/paused idle CPU:  near zero where architecture permits
```

These are engineering targets. Hardware claims require named physical evidence.

---

## 8. Correctness comes before the fast path

For cache/dirty-region/repair optimizations:

1. keep a simple correct path or equivalent oracle where practical;
2. make the fast path an accelerator, not the sole correctness implementation;
3. compare optimized output under identical inputs;
4. freeze time/randomness when needed;
5. include boundary states such as resize, locale change, round reset and animation completion.

Pixel/region equivalence is strongly preferred for rendering optimizations where practical.

Game rules need independent contract tests so visual optimization cannot silently change scoring, collision, completion or progression.

---

## 9. Audio engineering boundaries

Speech policy is defined by `VOICE_GENERATION.md`; microphone architecture is platform-owned.

Activity code must:

- request/use semantic audio cues where Greia resources own them;
- use shared character utterance families before duplicating generic praise/retry clips;
- use deterministic/system speech when the sound itself is educational truth;
- never enumerate/select microphone hardware or implement per-Activity denoising;
- obtain capture routing from `get_audio_capture_device()` when microphone access is granted;
- keep non-trivial audio sequencing/cancellation state in one explicit owner.

Loading/decoding a sound on every playback is the audio equivalent of loading an image every frame. Prepare bounded reusable playback resources.

---

## 10. Commenting and docstring standard

Comments preserve architectural intent; they do not narrate syntax.

Public/non-obvious Activity extension classes, protocols and state owners should document:

- responsibility;
- ownership/lifecycle;
- important invariants;
- dependencies;
- resource bounds where relevant;
- why a non-obvious performance/correctness/compatibility choice exists.

Good:

```text
# Keep this alias in main.py because Phase-4 compatibility tests and older
# maintainer tooling import it from the historical entrypoint.
```

Good:

```text
# Restore from the precomposited backdrop before drawing the lifted card;
# clearing to a flat color would corrupt wallpaper pixels around the tile.
```

Bad:

```text
# Increment x by one.
x += 1
```

Do not leave unexplained timing/cache-size constants. Name them and preserve the measurement/product reason where non-obvious.

If an Activity establishes a reusable pattern, update the relevant skill/design document instead of relying on one package's comments.

---

## 11. Testing and launch protocol

At minimum, cover the narrowest useful semantic contracts:

- domain/state transitions;
- round/challenge generation invariants;
- scoring/completion event emission;
- persistence serialization/migration;
- responsive/layout calculations where custom;
- semantic input behavior;
- cache bounds/invalidation;
- animation settle behavior;
- audio sequencing where non-trivial;
- optimized renderer equivalence where performance-sensitive.

For **modular Python Activities**, add runtime/tooling coverage too:

- package-local imports pass `PythonRuntimeAdapter` under the real runtime policy;
- forbidden/unknown external imports remain rejected;
- entrypoint works as the Greia script launch expects;
- repository package imports succeed;
- expected compatibility exports still exist or were deliberately migrated;
- readiness verification follows the lifecycle owner rather than assuming it is in `main.py`.

Then run the canonical validation/integration ladder. Current project commands include:

```bash
PYTHONPATH=src:tools python3 tools/validate_project.py
make verify
```

After source gates, **actually launch the Activity through the Greia Activity Simulator/launcher path** and exercise representative child interactions.

A successful `python main.py`, import, AST scan, or unit suite alone does not prove Greia launchability.

Do not claim the Simulator proves Acer/Pi performance, physical controller behavior, trusted system chrome, real microphone quality or production display/session architecture.

For performance work, report before/after measurements for the actual interaction and exact hardware/source scope claimed.

---

## 12. Activity engineering review gate

Before calling substantive Activity work complete, ask:

1. Is `main.py` only bootstrap/composition plus deliberately retained compatibility exports?
2. Does each module/class have one coherent ownership reason?
3. Is there already a Greia platform primitive/service that should own any new helper?
4. Are classes modeling state/lifecycle/invariants rather than being decorative wrappers?
5. Are genuine variation points polymorphic instead of repeated mode/type conditionals?
6. Is composition preferred over deep inheritance?
7. Are dependencies explicit and testable?
8. Are long-lived resources/caches bounded and cleaned up?
9. Is image/font/text/scale/IO/device/storage work absent from hot loops?
10. Does static presentation render only on invalidation where practical?
11. Does every cache have a complete key/invalidation story?
12. Does a rendering fast path fail back to a correct path?
13. Are gameplay semantics covered independently from presentation optimizations?
14. Are comments/docstrings explaining ownership, invariants and non-obvious why/compatibility decisions?
15. Could a new contributor find the correct extension point without reading a monolith?
16. Does the Activity obey platform ownership of Home/Back, input devices, microphone routing, storage, progression, localization and trust?
17. If modular, does the real runtime validator accept package-local imports without widening external authority?
18. Does it work in both runtime/script and repository/package import contexts?
19. Were legacy/public consumers searched before symbols moved?
20. Is READY still published exactly once after the first usable frame even if lifecycle code moved files?
21. Did project validation and required focused/full tests actually execute?
22. Did the Activity actually launch through the Greia Simulator/launcher path?
23. Were performance claims measured only at the scope actually tested?

If runtime validation or Simulator launch has not happened, describe the Activity as **integration-unverified**, not working/complete.

---

## 13. What not to do

Reject these patterns in new/substantively changed first-party Activities:

- 1,000+ line `main.py` applications;
- giant `Game`/`Manager` classes owning model + rendering + audio + storage + input;
- one event loop containing gameplay policy, image loads, font rendering and persistence writes;
- Activity-local copies of Greia storage/input/audio/localization/platform services;
- unbounded dicts used as caches;
- per-frame filesystem/device/subprocess/config work;
- per-frame image decode/scale/flip/static scenery generation;
- deep `BaseGame -> ... -> MyGame` inheritance stacks;
- interfaces invented for every concrete helper with no substitution need;
- Activity-specific module names added to the global runtime dependency allowlist;
- `sys.path` hacks scattered through Activity code;
- decomposition that works only as `python main.py` but breaks package imports;
- moving established exports without searching repository consumers;
- forcing lifecycle code back into `main.py` to satisfy a stale file-layout test instead of correcting the verifier's invariant;
- weakening forbidden-import/security rules to make modularization convenient;
- source-only testing followed by a claim that the Activity launches;
- performance fixes that change pixels/gameplay without equivalence/contract proof;
- undocumented hardware-tuned magic constants.

The intended result is simple, launchable code with strong seams—not enterprise ceremony and not architecture that exists only on paper.

# Greia Activity Refactoring Protocol

**Status:** mandatory companion for substantive Activity refactors  
**Audience:** coding agents, maintainers, reviewers  
**First calibrated on:** `activities/clinica_cuccioli` (2026-08-23)

Use this companion together with `CORE.md` and `ENGINEERING.md` whenever an existing Activity is being structurally refactored rather than merely receiving a tiny isolated fix.

The first calibration refactor exposed an important fact: monoliths hide contract drift as well as untidy code. A good refactor therefore starts by understanding behavior and authority, not by deciding filenames.

---

## 1. Before changing structure: inventory the Activity

Record, from source and `activity.toml`:

- Activity ID, runtime, input profile and capabilities;
- declared educational/progression event IDs;
- storage keys/schema version and durable values;
- supported UI/content locales and the actual localized resources used at runtime;
- external/shared Greia services consumed;
- audio jobs and whether they are speech, pedagogical audio or simple effects;
- main gameplay states and transitions;
- child input paths that can cause the same semantic action;
- renderer/static scenery/animation ownership;
- caches/resources and their lifecycle;
- any known simulator/physical behavior that must be preserved.

Then compare declaration with implementation. Do not assume they agree.

The Clinica Cuccioli calibration found two examples immediately:

- the manifest declared `vet.treatment_applied` / `vet.patient_healed`, while the monolith emitted `clinic.patient_cured`;
- palette clicks and patient taps used different correctness rules for the same treatment sequence.

Those are product/contract defects, not file-layout issues.

---

## 2. Classify changes before making them

Every refactor change belongs to one of these categories:

```text
STRUCTURAL PRESERVATION
    same behavior, clearer ownership/module boundaries

CONTRACT REPAIR
    implementation brought back into agreement with manifest/API/ADR/product authority

BEHAVIOR FIX
    inconsistent or clearly defective child-facing behavior intentionally corrected

PERFORMANCE STRUCTURE
    source architecture changed to remove known hot-path work or enable measurement
```

Do not smuggle a behavior redesign inside a structural refactor. When a behavior changes intentionally, name it and add a narrow test.

Do not claim a source-level performance structure change improved physical performance until it is measured on the claimed hardware/evidence lane.

---

## 3. Preferred extraction order for a monolithic Python Activity

For a typical giant `main.py`, this order has proven effective:

1. **Pure domain/state model first**
   - rules, invariants, round/treatment state, scoring state;
   - no Pygame, storage, audio or Greia event IO;
   - inject randomness/clock only where determinism matters.

2. **Platform/service adapters second**
   - Greia storage mapping;
   - declared event publication;
   - Activity-specific service ports where tests/alternate implementations genuinely need substitution.

3. **Presentation/resource owner third**
   - renderer geometry;
   - prepared assets/text;
   - bounded transient FX;
   - static backdrop/caches and invalidation.

4. **Application/lifecycle coordinator fourth**
   - event loop;
   - semantic input routing;
   - ordering calls between domain, audio, persistence/events and renderer;
   - no duplicated business rules.

5. **`main.py` last**
   - construct runtime context and collaborators;
   - enter the application;
   - top-level cleanup only.

This order is a default, not a mandatory filename scheme. It prevents the common failure mode where a monolith is split into several files but the state/ownership tangle remains unchanged.

---

## 4. OOP/polymorphism calibration from real Activity work

Use objects for owners; keep pure drawing/math as functions when no lifecycle/state belongs there.

The Clinica Cuccioli split is intentionally mixed:

```text
ClinicSession
    object: owns gameplay state and sequencing invariants

ClinicActivity
    object: owns runtime/event-loop coordination

ClinicRenderer
    object: owns prepared presentation resources, geometry and transient FX

PygameClinicAudio
    object: owns the prepared mixer sound bank

ClinicProgressPort / ClinicEventPort / ClinicAudioPort
    protocols: real substitution seams used by application tests/runtime adapters

procedural animal/tool drawing helpers
    functions: stateless rendering calculations; no fake class required
```

This is the desired balance. "Strong OOP" does not mean turning every function into a class.

Do not add a protocol just because a class exists. Add one when the caller benefits from substituting implementations (tests, runtime adapter, alternate strategy) and keep it narrow.

---

## 5. One semantic action must have one rule

When multiple input routes trigger the same child action (pointer palette, patient tap, keyboard/controller activation, touch, etc.), translate them into one domain operation.

Do not duplicate correctness/scoring rules in each input branch.

Bad:

```text
palette branch decides whether treatment is valid
patient branch separately decides whether treatment is valid
controller branch later implements a third interpretation
```

Good:

```text
input route -> semantic tool/action -> ClinicSession.use_tool(...)
```

The input layer chooses *what action the child attempted*; the domain owner decides *what that action means*.

---

## 6. Cross-check manifest contracts during refactor

Before completion, compare code against `activity.toml` for at least:

- event IDs actually emitted;
- required capabilities actually used;
- input profile assumptions;
- package entrypoint;
- storage schema/key behavior;
- declared language support versus visible strings/audio actually used;
- permissions and shared-service access.

A multilingual declaration is not enough. If the Activity has package localization bundles, visible text should actually resolve through the localization layer rather than staying hard-coded in one language.

Where useful, add a test that reads the manifest and asserts the adapter emits only declared event IDs. This is stronger than separately testing the manifest and implementation while never comparing them.

---

## 7. Performance structure to look for while decomposing

A monolith often hides repeated work. During extraction, identify which owner can prepare it once.

Useful patterns from the Clinica Cuccioli calibration:

- static wallpaper/floor/table -> one pre-rendered opaque backdrop;
- finite tool labels/states -> finite cached text surfaces;
- generated sound effects -> synthesize once when the audio owner is constructed;
- particle effects -> explicit bounded owner/list;
- full-screen translucent victory modal -> compose once, freeze to an opaque frame while static;
- static victory state -> stop repainting unchanged pixels; retain bounded polling for stop/input latency.

Do not generalize these exact caches to every Activity. Apply the principle to the measured/obvious working set and preserve an invalidation story.

Source inspection can justify removing obviously prohibited hot-loop work. It does **not** establish Acer/Pi before/after numbers; physical claims still require measurement.

---

## 8. Refactor tests

Prefer a small set of high-value tests over tests that mirror implementation details.

For a monolith extraction, normally add:

- pure domain transition/invariant tests;
- one test for each intentional behavior fix;
- manifest-to-event adapter consistency where events exist;
- persistence mapping tests when migration/state shape changes;
- renderer equivalence/performance-sensitive tests when optimizing visuals;
- simulator/manual checks for integration facts not covered by pure tests.

Do not assert arbitrary file counts or enforce the engineering guide's review line thresholds as mechanical tests. Those thresholds are review prompts, not product behavior.

---

## 9. Completion review

Before calling an Activity refactor complete:

1. Can gameplay rules be understood without opening the renderer/event loop?
2. Can renderer changes be made without editing scoring/persistence rules?
3. Do all input routes delegate semantic truth to the same domain operation?
4. Does `main.py` only compose/start/clean up?
5. Do platform side effects live behind narrow owners/adapters?
6. Do emitted event IDs match the manifest?
7. Does declared localization correspond to actual localized runtime presentation?
8. Are caches/transient collections bounded with clear lifecycle/invalidation?
9. Did the refactor remove obvious hot-loop IO/decode/render-allocation work without inventing performance claims?
10. Are intentional behavior fixes distinguished from structural preservation and tested?
11. Is there a clear candidate for platform extraction if the same helper appears in other Activities?
12. Did documentation/skill guidance get refined when the refactor taught a reusable lesson?

The purpose is not to make the Activity look "architected". The purpose is to make the next feature safer, faster and more consistent to implement.

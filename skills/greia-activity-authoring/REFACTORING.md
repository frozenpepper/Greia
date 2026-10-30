# Greia Activity Refactoring Protocol

**Status:** mandatory companion for substantive Activity refactors  
**Audience:** coding agents, maintainers, reviewers  
**First calibrated on:** `activities/clinica_cuccioli`  
**Calibration correction:** the first structural pass was architecturally cleaner but **did not launch** until runtime/tooling contracts were repaired. A second local pass then proved that **launching is still not acceptance**: child interaction semantics and the complete-session/end-screen path must also be exercised. This document deliberately preserves both lessons.

Use this companion together with `SKILL.md` and `ENGINEERING.md` whenever an existing Activity is being structurally refactored rather than merely receiving a tiny isolated fix.

A refactor is not successful because the code is cleaner, imports on one developer path, launches once, or has newly authored unit tests. It is successful only when the Activity still satisfies its **product, package, runtime, lifecycle, compatibility, interaction and terminal-state contracts** and has actually passed the appropriate integration gate.

---

## 1. Before changing structure: inventory the Activity and its consumers

Record, from source, `activity.toml`, repository tests and tooling:

- Activity ID, runtime, entrypoint, input profile and capabilities;
- declared educational/progression event IDs;
- storage keys/schema version and durable values;
- supported UI/content locales and the actual localized resources used at runtime;
- external/shared Greia services consumed;
- audio jobs and whether they are speech, pedagogical audio or simple effects;
- main gameplay states and transitions, including completion/restart;
- child input paths that can cause the same semantic action;
- what each child gesture is supposed to mean: select, apply, confirm, navigate, retry, etc.;
- any default/automatic selection state and whether it represents a real child choice or merely internal knowledge of the correct answer;
- renderer/static scenery/animation ownership;
- caches/resources and their lifecycle;
- READY/STOP lifecycle behavior and where `mark_activity_ready()` is reached;
- imports/exports other repository code or tests consume from the Activity;
- runtime-validator assumptions that apply to the entrypoint and package Python files;
- any known Simulator/physical behavior that must be preserved.

Then compare declaration with implementation. Do not assume they agree.

### Compatibility-surface search is mandatory

Before moving a symbol out of `main.py` or another established module, search the repository for imports and references to it.

Historical first-party tests or tools may import symbols such as:

```python
from activities.some_activity.main import SOME_TABLE, SomeAudio
```

That is a compatibility contract until it is deliberately migrated. Choose one of two explicit paths:

1. preserve a small compatibility alias/export in the old location; or
2. migrate every legitimate consumer in the same coherent tranche and document the break.

Do not discover these consumers only after the full suite fails.

### What the Clinica Cuccioli calibration found

The first pass uncovered useful semantic defects:

- the manifest declared `vet.treatment_applied` / `vet.patient_healed`, while the monolith emitted `clinic.patient_cured`;
- palette clicks and patient taps used different correctness rules for the same treatment sequence;
- Italian + English were declared but some visible UI remained hard-coded Italian.

But the first pass also missed integration contracts and therefore **did not launch**:

- `PythonRuntimeAdapter` rejected new package-local sibling imports as if they were unapproved external dependencies;
- direct-script imports worked while repository package imports failed;
- established `PATIENTS`, `TOOLS` and `VetAudio` exports disappeared from `main.py`;
- the readiness verifier assumed `mark_activity_ready()` must live directly in the runtime entrypoint.

After those launch failures were repaired and the Simulator could start the Activity, a second acceptance pass found two more product/runtime defects:

- `ClinicSession` automatically selected the first correct tool and automatically armed the next correct tool after every successful treatment, so tapping the animal could effectively perform the answer for the child;
- the terminal victory path crashed after a complete session, while startup and ordinary treatment still worked.

A good refactoring protocol has to catch all three categories: source architecture, launch/runtime compatibility, and the actual child-facing state machine from first interaction through completion and restart.

---

## 2. Classify changes before making them

Every refactor change belongs to one of these categories:

```text
STRUCTURAL PRESERVATION
    same product/runtime behavior, clearer ownership/module boundaries

CONTRACT REPAIR
    implementation brought back into agreement with manifest/API/ADR/runtime/tooling authority

BEHAVIOR FIX
    inconsistent or clearly defective child-facing behavior intentionally corrected

PERFORMANCE STRUCTURE
    source architecture changed to remove known hot-path work or enable measurement

COMPATIBILITY MIGRATION
    an established import/export/tooling surface is deliberately preserved or migrated
```

Do not smuggle a behavior redesign inside a structural refactor. When behavior changes intentionally, name it and add a narrow test.

Do not silently weaken runtime security or widen a dependency allowlist just to make decomposition convenient.

Do not claim a source-level performance structure change improved physical performance until it is measured on the claimed hardware/evidence lane.

---

## 3. Prove the architecture is supported before decomposing

The architecture we want and the architecture the current platform/tooling actually accepts must agree.

Before splitting a Python Activity into sibling modules, inspect the current owners of the launch contract:

```text
activity.toml
runtime/child-runtime.toml
src/greia_launcher/runtime_adapter.py
tools/validate_project.py
relevant first-party Activity verification tests
```

### Package-local imports are not external dependencies

Greia's Python runtime deliberately curates external import roots. Code stored inside the validated Activity package is different: it is part of the same Activity package and may be split into local modules.

The runtime validator must therefore distinguish:

```text
forbidden root
    always reject

package-local module/package under manifest.root
    allow as Activity code

curated external root
    allow

unknown external root
    reject
```

Do **not** solve a package-local import failure by adding `my_activity_model`, `clinic_renderer`, etc. to the global external allowlist. That would encode one Activity's filenames into platform policy and destroy the meaning of the curated runtime boundary.

Likewise, a local file must not be allowed to shadow a curated platform/external module. The runtime owner remains responsible for anti-shadowing and package-boundary validation.

### Platform validators/tests must not freeze monolithic architecture

A verifier may enforce a semantic invariant such as:

> READY is published once, after a usable frame has been presented.

It should not accidentally enforce:

> the READY call must be textually located in `main.py`.

If a legitimate decomposition moves lifecycle code to `app.py`, update the verifier to inspect the relevant package modules while preserving the semantic invariant. Do not move lifecycle logic back into `main.py` merely to satisfy a stale structural assumption.

This principle applies to other tooling too: validators should verify contracts, not an incidental old file layout.

---

## 4. Preferred extraction order for a monolithic Python Activity

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
   - READY publication after first usable presentation;
   - no duplicated business rules.

5. **`main.py` last**
   - construct runtime context and collaborators;
   - retain required compatibility exports where needed;
   - enter the application;
   - top-level cleanup only.

This order is a default, not a mandatory filename scheme. It prevents the common failure mode where a monolith is split into several files but the state/ownership tangle remains unchanged.

---

## 5. Python module/import contract for decomposed Activities

Greia Python Activities have at least two legitimate execution contexts that refactoring must support:

```text
runtime/script context
    Greia executes manifest.entrypoint as a file with cwd at the Activity root

repository/package context
    tests/tools may import activities.<activity>.main or sibling modules as package modules
```

An import layout that works only in one context is incomplete.

### Recommended compatibility pattern

For new code, prefer an explicit package-context branch rather than catching every possible import failure:

```python
if __package__:
    from .model import ActivityModel
    from .renderer import ActivityRenderer
else:
    from model import ActivityModel
    from renderer import ActivityRenderer
```

A narrow `try`/fallback import compatibility block is acceptable where already established and verified, but be aware that broad `except ImportError` can accidentally catch an ImportError raised *inside* the imported module and obscure the real defect.

Do not manipulate `sys.path` ad hoc inside each Activity merely to compensate for unclear package semantics.

### Required import checks

For a decomposed Activity, prove at minimum:

- the real `PythonRuntimeAdapter` validates the package using the current `runtime/child-runtime.toml` policy;
- the declared entrypoint can run in the runtime/script context;
- the Activity can be imported through the repository package context used by tests;
- package-local modules do not require widening the external import allowlist;
- forbidden imports remain forbidden.

---

## 6. OOP/polymorphism calibration from real Activity work

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

Do not promote an Activity-local abstraction into `greia_platform` after seeing it only once. Compare at least one or two additional Activities and confirm that the semantics—not just the filenames—are genuinely shared.

---

## 7. One semantic action must have one rule — and child choice must remain child choice

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
input route -> semantic tool/action -> domain rule
```

The input layer chooses *what action the child attempted*; the domain owner decides *what that action means*.

### Do not confuse known answer with selected answer

The domain often knows the correct/current answer (`next_needed`, target shape, correct number, etc.). That internal truth must not silently become the child's selected input unless the product explicitly intends auto-selection.

For a two-step interaction such as:

```text
choose tool -> use tool on patient
```

keep those states separate:

```text
next_needed          pedagogical/domain truth
selected_tool_id     actual child choice, possibly None
```

After a successful application, clear the child selection if the next step is supposed to require another explicit choice. Do **not** automatically set:

```python
selected_tool_id = next_needed
```

merely because the domain knows what comes next.

This applies beyond clinic games: selection/focus/drag source/answer candidate must represent the child's action, not a convenience mirror of the correct solution.

---

## 8. Cross-check manifest and lifecycle contracts during refactor

Before completion, compare code against `activity.toml` and runtime ownership for at least:

- event IDs actually emitted;
- required capabilities actually used;
- input profile assumptions;
- package entrypoint;
- storage schema/key behavior;
- declared language support versus visible strings/audio actually used;
- permissions and shared-service access;
- READY/STOP lifecycle behavior;
- public/legacy imports and exports used by repository consumers.

A multilingual declaration is not enough. If the Activity has package localization bundles, visible text should actually resolve through the localization layer rather than staying hard-coded in one language.

Where useful, add a test that reads the manifest and asserts the adapter emits only declared event IDs. This is stronger than separately testing the manifest and implementation while never comparing them.

### READY ownership

`mark_activity_ready()` belongs where the application actually knows that a usable frame has been presented. That may be an app/lifecycle module rather than `main.py`.

The invariant is:

```text
first usable frame presented
    -> publish READY exactly once
```

not a textual requirement about which source file contains the call.

Repository verification should follow that semantic architecture, and the actual runtime launch path must demonstrably reach the READY publication.

---

## 9. Performance structure to look for while decomposing

A monolith often hides repeated work. During extraction, identify which owner can prepare it once.

Useful patterns from the Clinica Cuccioli calibration:

- static wallpaper/floor/table -> one pre-rendered opaque backdrop;
- finite tool labels/states -> finite cached text surfaces;
- generated sound effects -> synthesize once when the audio owner is constructed;
- particle effects -> explicit bounded owner/list;
- finite terminal overlay/labels -> prepare once with the presentation owner;
- static victory state -> stop repainting unchanged pixels while retaining bounded polling for stop/input latency.

### Do not stack caches on top of an invalidation system without a measured reason

The first refactor added a second optimization to the victory screen: after composing the terminal frame, it copied the full 1024×600 surface into a reusable cache. But `ClinicActivity` already used dirty rendering and did not repaint the unchanged victory state. The full-frame cache therefore duplicated ownership, added memory/allocation/state complexity on the final transition, and had no normal-frame reuse job to perform.

Prefer:

```text
state changes -> renderer draws once -> dirty becomes false -> no repaint
```

over:

```text
state changes -> renderer draws once -> copy whole frame -> cache it
-> app also stops repainting anyway
```

A cache must solve repeated measured/obvious work. If the caller already prevents that work from recurring, an extra cache is usually not an optimization.

Likewise, terminal/end screens should have an explicit render path when active-game assumptions no longer hold. Prepare finite resources up front where practical so completion is not the first time a font, large alpha surface or other known resource is created.

Do not generalize these exact caches to every Activity. Apply the principle to the measured/obvious working set and preserve an invalidation story.

Source inspection can justify removing obviously prohibited hot-loop work. It does **not** establish Acer/Pi before/after numbers; physical claims still require measurement.

---

## 10. Required refactor verification ladder

A structural Activity refactor is **not complete** after unit tests are merely authored.

Run the narrowest useful checks first, then the integration gates:

### 10.1 Pure/domain checks

Cover:

- domain transition/invariant tests;
- each intentional behavior fix;
- selection/input state separately from correct-answer/domain state where relevant;
- manifest-to-event consistency where events exist;
- persistence mapping when migration/state shape changes;
- cache/render equivalence where a performance path changed;
- completion and restart transitions.

### 10.2 Runtime/package validation

Use the real project validator/runtime policy. Current standard validation includes:

```bash
PYTHONPATH=src:tools python3 tools/validate_project.py
```

Also run focused runtime-adapter/readiness tests whenever decomposition changed Python module or lifecycle layout.

### 10.3 Repository compatibility tests

Run focused historical/Activity tests that import the Activity as a package. This is where lost public exports and package-context import defects are expected to surface.

Then run the full repository gate required by the project, normally:

```bash
make verify
```

Do not wave away failures as "legacy tests" until you have established whether they represent an intentional compatibility contract. Preserve aliases or deliberately migrate consumers.

### 10.4 Actual Activity Simulator acceptance

Launch the Activity through the real Greia Activity Simulator/launcher path.

Do not substitute:

- `python main.py` alone;
- importing the module alone;
- AST/source tests alone;
- a successful package validator alone;
- seeing the first frame alone.

A refactor that passes all source tests but the Simulator refuses to launch is failed acceptance. A refactor that launches but has broken child interactions or crashes at completion is also failed acceptance.

For a stateful Activity, exercise the **complete happy path**, not a two-click smoke test. At minimum cover the applicable sequence:

```text
launch
-> first meaningful child action
-> wrong/alternate action where relevant
-> repeated normal progress
-> score/progression update
-> final round/patient/challenge
-> terminal/victory/completion screen
-> terminal input such as Play Again / Continue
-> restart or clean exit
```

Also exercise any materially different input route the Activity claims to support.

### 10.5 Physical evidence when relevant

The Simulator does not prove Acer/Pi performance, physical controller behavior, production display/session authority or real microphone quality. Use named physical evidence for those claims.

---

## 11. Completion review

Before calling an Activity refactor complete, answer **yes** to the relevant questions:

1. Can gameplay rules be understood without opening the renderer/event loop?
2. Can renderer changes be made without editing scoring/persistence rules?
3. Do all input routes delegate semantic truth to the same domain operation?
4. Does actual child selection remain separate from the domain's knowledge of the correct answer?
5. Does `main.py` only compose/start/clean up plus deliberately retained compatibility exports?
6. Do platform side effects live behind narrow owners/adapters?
7. Do emitted event IDs match the manifest?
8. Does declared localization correspond to actual localized runtime presentation?
9. Are caches/transient collections bounded with clear lifecycle/invalidation?
10. Does every cache remove recurring work that is not already eliminated by caller invalidation/dirty rendering?
11. Did the refactor remove obvious hot-loop IO/decode/render-allocation work without inventing performance claims?
12. Are intentional behavior fixes distinguished from structural preservation and tested?
13. Were old imports/exports searched and either preserved or deliberately migrated?
14. Does the current runtime validator accept the decomposed package without widening external dependency authority?
15. Does the Activity work both in runtime/script and repository/package import contexts?
16. Does READY still publish once after the first usable presented frame even if lifecycle ownership moved modules?
17. Did `tools/validate_project.py` (or the current canonical validator) pass on the refactored package?
18. Did the required focused and full repository tests actually execute and pass, or are any failures explicitly unresolved?
19. Did the Activity actually launch through the Greia Simulator and survive the complete representative child flow through completion?
20. Did the terminal/victory screen render successfully and did Continue/Play Again/restart or exit behave correctly?
21. Is there a clear candidate for platform extraction only if the same semantics appear in other Activities?
22. Did documentation/skill guidance get refined when the refactor taught a reusable lesson?

If the runtime or Simulator gate has not run through the relevant terminal/restart path, label the work **source-refactored / integration-unverified**, not complete or working.

# Clinica Cuccioli — Activity Architecture Calibration Refactor

**Date:** 2026-08-23  
**Activity:** `org.greia.clinica-cuccioli`  
**Purpose:** first real calibration of the strengthened Activity engineering/refactoring skill  
**Final disposition:** **INITIAL REFACTOR FAILED LAUNCH ACCEPTANCE; FOLLOW-UP FIX VERIFIED LOCALLY**

---

## 1. Why this Activity was selected

`activities/clinica_cuccioli/main.py` was approximately **33.5 KB** and owned essentially the entire product implementation in one file:

- treatment/round state;
- random prescription generation;
- scoring/stars;
- durable storage writes;
- Greia event publication;
- procedural audio synthesis and playback;
- input handling;
- protected-region checks;
- particle state;
- all animal/tool drawing;
- full scene rendering;
- localization imports not actually used by some visible controls;
- lifecycle/READY handling.

It does **not** require new Greia character voice generation. Its audio is simple procedural effects, so it was suitable for an architecture calibration without adding a voice-production dependency.

---

## 2. Structural result of the first pass

The first pass decomposed the monolith into:

```text
main.py
    thin composition root

clinic_model.py
    ClinicSession / TreatmentResult
    prescription/gameplay invariants

clinic_app.py
    ClinicActivity
    event-loop lifecycle
    semantic input -> domain orchestration

clinic_renderer.py
    ClinicRenderer
    stable geometry
    prepared/cached presentation
    bounded particles

clinic_art.py
    stateless procedural animal/tool drawing helpers

clinic_audio.py
    ClinicAudioPort / PygameClinicAudio
    one-time procedural SFX preparation

clinic_services.py
    ClinicProgressPort / GreiaClinicProgress
    ClinicEventPort / GreiaClinicEvents
```

That responsibility split remains directionally correct. Strong OOP did not mean forcing stateless drawing helpers into classes: state/lifecycle/resource owners became objects; pure drawing stayed functional.

However, **clean structure was not sufficient**. The first pass had not been executed through the real Greia runtime/Simulator acceptance path and the Activity did not launch.

---

## 3. Semantic/product defects correctly found in the first pass

The initial refactor did reveal legitimate problems hidden by the monolith.

### 3.1 Event contract drift

`activity.toml` declares:

```text
vet.treatment_applied
vet.patient_healed
```

The old monolith emitted:

```text
clinic.patient_cured
```

The refactored `GreiaClinicEvents` adapter publishes the manifest-declared IDs, and provider-free coverage compares emitted IDs with the manifest.

### 3.2 Inconsistent sequencing semantics

The UI presented an ordered prescription, but the old implementation had two rules:

- palette clicks could apply any still-required treatment, including a later step;
- patient taps accepted only the exact next step.

`ClinicSession` now owns one treatment-sequencing rule and all input paths delegate to it. This was an intentional **behavior fix**, not structural preservation.

### 3.3 Declared localization was not fully consumed

The package declares Italian and English and already had locale bundles, but visible palette/victory text was partly hard-coded Italian. The renderer now consumes `LocalizedResources` for those visible labels. No new generated speech was introduced.

---

# 4. Initial launch failure — calibration correction

The first refactor was initially described as a coherent source state with authored tests, but **it was not a working Greia Activity**. Local integration exposed four separate failures.

This is the most important lesson of the calibration.

## 4.1 PythonRuntimeAdapter rejected package-local sibling modules

Greia's Python runtime validates every Activity Python file through AST inspection and the curated policy in:

```text
runtime/child-runtime.toml
src/greia_launcher/runtime_adapter.py
```

Before the fix, import validation distinguished only:

```text
allowed external root
forbidden/unknown root
```

It did not distinguish **Python modules physically contained inside the already validated Activity package**.

After decomposition, imports such as:

```python
from clinic_audio import ClinicAudioPort
from clinic_model import ClinicSession
```

were therefore rejected with an error equivalent to:

```text
RuntimeValidationError: Python import 'clinic_audio' is outside the curated child runtime
```

### Correct architectural fix

Commit:

```text
d0aa76a003e397128326a3f932e4a2b7248058ae
```

updated `PythonRuntimeAdapter` so import authority is evaluated in this order:

```text
forbidden import root
    reject

module/package present under manifest.root
    allow as package-local Activity code

curated external import root
    allow

unknown external root
    reject
```

This preserves the security model. Activity-specific module names were **not** added to the global external allowlist.

A runtime-manager regression test now explicitly validates package-local imports.

## 4.2 Direct-script and repository-package imports differed

Greia executes the Activity entrypoint as a script from the Activity root. Repository tests may instead import:

```python
from activities.clinica_cuccioli.main import ...
```

Top-level sibling imports worked in the first context but failed in the second because the Activity directory was not independently added to `sys.path`.

The follow-up fix added compatible sibling import handling in:

```text
main.py
clinic_app.py
clinic_renderer.py
clinic_services.py
```

This established a reusable requirement: modular Activities must be tested both as runtime scripts and as repository package imports.

Future new code should prefer an explicit `__package__`-aware import branch where practical so an unrelated `ImportError` inside an imported module is not accidentally hidden by a broad fallback handler.

## 4.3 Established exports disappeared

Historical Phase-4 tests legitimately imported:

```text
PATIENTS
TOOLS
VetAudio
```

from `activities.clinica_cuccioli.main`.

The refactor moved/renamed the underlying implementation without first inventorying those consumers. The follow-up restored narrow compatibility exports in `main.py`.

This does **not** invalidate the thin-composition-root principle. A thin entrypoint may retain a few documented compatibility aliases. The lesson is to search repository consumers before moving established symbols.

## 4.4 Readiness verification encoded the old file layout

`tests/test_first_party_activity_readiness.py` correctly wants to verify the semantic invariant:

```text
present first usable frame -> mark Activity READY exactly once
```

But the old test only inspected the manifest entrypoint file. Once the lifecycle moved to `clinic_app.py`, the verifier could no longer see the READY call.

The fix made readiness verification inspect candidate Python modules inside the Activity package while retaining the actual semantic check that frame presentation precedes READY.

The correct response was **not** to move lifecycle logic back into `main.py`. Tooling had encoded a monolithic implementation detail and needed to become architecture-aware.

---

# 5. Follow-up verification reported by the local owner-controlled lane

After the follow-up fixes, the user reported the following local results for the corrected tranche:

### Project validator

```bash
PYTHONPATH=src:tools python3 tools/validate_project.py
```

Reported result:

```text
PASS runtime_api=0.1 activities=19 ... image_profiles=10 runtimes=python
```

### Full test suite

Reported result:

```text
1096 passed, 9 warnings in 52.84s
```

### Activity Simulator

Reported result:

```text
Clinica Cuccioli validates cleanly and launches directly from the Simulator UI.
```

These results are the evidence that converts the Activity from an architecture-only refactor into a locally accepted integration result. They should not be extrapolated into Acer/Pi performance claims.

---

# 6. Performance-structure changes retained

The refactor's source-level performance improvements remain useful:

- static clinic scenery is pre-rendered once to an opaque backdrop;
- finite localized tool labels are cached;
- star text caches the current rendered value;
- particles are typed and explicitly bounded;
- procedural SFX are synthesized once by the audio owner;
- the victory modal pays the large alpha composition once then reuses an opaque composed frame;
- a static victory state need not repaint unchanged pixels while still polling input/STOP responsively.

Active treatment remains intentionally animated around 30 Hz for the thought bubble and transient effects.

No physical frame-time/CPU improvement is claimed without hardware measurement.

---

# 7. Skill changes produced by the failed acceptance

The first version of the Activity engineering guidance was too focused on internal source quality. It now explicitly treats **runtime/tooling compatibility as part of architecture correctness**.

Updated:

```text
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-activity-authoring/REFACTORING.md
```

New mandatory lessons include:

1. Search existing repository imports/exports before structural movement.
2. Inspect the real runtime validator and policy before decomposing Python code.
3. Package-local modules are Activity code, not external dependencies; do not solve local-import failures by widening the global dependency allowlist.
4. Support and test both runtime/script and repository/package import contexts.
5. Preserve compatibility aliases or migrate all legitimate consumers coherently.
6. Verification should enforce semantic lifecycle invariants rather than incidental file placement.
7. `mark_activity_ready()` may live in the lifecycle owner rather than the entrypoint as long as the real launch path reaches it after first usable presentation.
8. Modular Activity work requires real runtime/package validation, not only pure unit tests.
9. Run the canonical project validator and full repository gate.
10. **Actually launch the Activity through the Greia Simulator/launcher path before calling it working or complete.**
11. If Simulator/runtime validation has not run, label the state `integration-unverified`.
12. When an architecture change exposes stale tooling, evolve the tooling to verify the real invariant; do not force good code back into a monolith and do not weaken security.

---

# 8. Broader architecture lesson

The most useful conclusion is not specific to Clinica Cuccioli:

> **A refactor changes more than source files. It changes assumptions made by validators, launchers, tests and compatibility consumers. Those assumptions are part of the architecture and must be audited in the same tranche.**

This is especially important in Greia because Activities execute inside a deliberately curated/supervised runtime rather than a generic unconstrained Python environment.

The desired architecture remains modular and OOP-clean. The corrected standard simply requires that the platform/tooling be capable of supporting that architecture before we call the work complete.

---

# 9. Next calibration step

Before promoting any Clinic-local abstractions into `greia_platform`, refactor or deeply review at least one or two Activities with different mechanics and compare actual recurring semantics.

Candidates worth comparing include:

- application/event-loop coordination;
- bounded transient FX ownership;
- progress/event adapter shape;
- static reference-canvas backdrop preparation;
- common runtime/package import conventions.

Do not extract a universal framework from a single example.

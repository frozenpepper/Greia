# Clinica Cuccioli — Activity Architecture Calibration Refactor

**Date:** 2026-08-23  
**Activity:** `org.greia.clinica-cuccioli`  
**Purpose:** first real calibration of the strengthened Activity engineering/refactoring skill  
**Evidence scope:** SOURCE / authored tests only; no simulator or physical performance claim in this tranche

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
- localization imports that were not actually used for the visible controls;
- lifecycle/READY handling.

It does **not** require new Greia character voice generation. Its audio is small procedural sound effects, making it suitable for an architecture calibration without adding a voice-production dependency.

---

## 2. Contract/behavior inventory findings

The refactor immediately found defects that a file-splitting exercise alone could have missed.

### 2.1 Event contract drift

`activity.toml` declares:

```text
vet.treatment_applied
vet.patient_healed
```

The old monolith emitted:

```text
clinic.patient_cured
```

The new `GreiaClinicEvents` adapter publishes only the declared IDs and a provider-free test compares emitted IDs against the manifest.

### 2.2 Inconsistent sequencing semantics

The UI presented an ordered prescription, but two input paths had different rules:

- clicking a palette tool applied any still-required treatment, even if it was a later step;
- tapping the patient applied treatment only when the selected tool was the exact next step.

The extracted `ClinicSession` now owns one rule: only the visible next prescription step applies. All input paths delegate to that same domain operation.

This is recorded as an intentional **BEHAVIOR FIX**, not disguised as structural preservation.

### 2.3 Multilingual declaration versus runtime UI

The package declares Italian and English and already carried both locale bundles, but the tool palette and victory UI were hard-coded in Italian inside the render loop.

The composition root now resolves `LocalizedResources` from `get_profile_locale()`, and the renderer consumes semantic localized short-label keys. No new spoken assets were introduced.

---

## 3. New responsibility structure

```text
main.py
    composition root only

clinic_model.py
    ClinicSession
    TreatmentResult
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
    ClinicAudioPort
    PygameClinicAudio
    one-time procedural SFX preparation

clinic_services.py
    ClinicProgressPort / GreiaClinicProgress
    ClinicEventPort / GreiaClinicEvents
```

This deliberately demonstrates that strong OOP does **not** mean every helper becomes a class. Stateful/lifecycle/resource owners are objects; stateless drawing calculations remain functions.

The new `main.py` is approximately 2 KB and now only resolves localization/runtime collaborators, constructs the owners and runs the application.

---

## 4. OOP/polymorphism lessons

Useful seams discovered through real work:

- `ClinicSession` is a domain object because it owns treatment invariants and mutable session state.
- `ClinicRenderer` is an object because it owns prepared surfaces, finite text caches, geometry and transient visual state.
- `PygameClinicAudio` is an object because it owns mixer resources and a prepared sound bank.
- `ClinicActivity` is an application/lifecycle coordinator rather than a god `Game` class.
- audio, progress and event Protocols are justified because the application should be testable with substitutes and should not encode platform IO directly.
- procedural animal/tool drawing remains functional because there is no useful object lifecycle or substitution seam there.

This balance is now captured in `skills/greia-activity-authoring/REFACTORING.md`.

---

## 5. Performance-structure improvements

These are source-architecture improvements only; no physical speedup is claimed until measured.

Old hot-loop behavior included:

- rebuilding wallpaper stripes/floor/table every frame;
- rendering the same five tool labels every frame;
- allocating and alpha-blending a full-screen victory overlay every victory frame;
- keeping particle state as untyped dictionaries inside the main loop;
- all sound synthesis embedded in the same monolith.

New structure:

- static clinic scenery is pre-rendered once to one opaque backdrop;
- finite tool/state labels are cached with a naturally bounded working set;
- star text keeps only the current rendered value;
- particles are typed and explicitly capped at 96;
- procedural sound effects are synthesized once by the audio owner;
- the victory modal pays the large alpha composition once, then freezes the composed result to an opaque cached frame;
- while the victory frame is unchanged the app continues bounded input/stop polling but does not repaint unchanged pixels.

Active treatment remains intentionally animated at ~30 Hz because the thought bubble bobs and success particles move.

---

## 6. Tests authored

Added:

```text
tests/test_clinica_cuccioli_refactor.py
```

Coverage includes:

- deterministic prescription generation through an injected random source;
- one ordered treatment rule;
- successful treatment/heal transitions;
- five-patient completion;
- star persistence across in-session restart semantics;
- final healed-patient identity at victory;
- event adapter IDs checked against `activity.toml`;
- rejection of the stale `clinic.patient_cured` event identity.

These tests are **AUTHORED, NOT EXECUTED** in the GitHub editing environment used for this tranche.

Required local verification:

```bash
PYTHONPATH=src python3 -m unittest discover \
  -s tests -p 'test_clinica_cuccioli_refactor.py' -v

make verify
```

Then load `activities/clinica_cuccioli` through the real Activity Simulator and verify at least:

1. Italian profile: palette/victory labels are Italian.
2. English profile: palette/victory labels are English.
3. Selecting a later prescription tool does not mark that later treatment complete.
4. The visible next treatment succeeds from the palette and from selected-tool patient interaction.
5. Each correct treatment produces its effect and treatment event; each healed patient awards exactly one star/heal event.
6. Five patients reach the victory screen and Play Again preserves total stars.
7. resize/viewport mapping remains usable;
8. Greia Home/protected-region behavior remains intact;
9. no Linux/browser/desktop surface is exposed.

Physical Acer performance may be measured later, but source inspection alone must not create before/after CPU or frame-time claims.

---

## 7. Skill refinements made from this calibration

Created:

```text
skills/greia-activity-authoring/REFACTORING.md
```

and wired it into the main Activity-authoring skill.

New reusable guidance includes:

- inventory behavior + manifest/platform contracts before structural edits;
- classify changes as structural preservation, contract repair, behavior fix or performance structure;
- prefer extraction order: pure domain -> platform adapters -> presentation/resources -> app coordinator -> thin `main.py`;
- multiple input paths for one semantic action must delegate to one domain rule;
- compare emitted events directly with manifest declarations;
- verify declared localization is actually consumed at runtime;
- do not force stateless helpers into classes merely to appear object-oriented;
- use Protocols at real substitution/test seams;
- refactor tests should guard semantic contracts, not arbitrary file counts;
- source-level performance cleanup is not physical evidence.

---

## 8. Open follow-up after local execution

Do not treat this calibration as final until the focused test + aggregate gate + simulator smoke have run.

If they expose defects, fix the architecture rather than restoring the monolith. After the first successful simulator/device comparison, decide whether any of the following deserve shared Greia extraction:

- a reusable small Activity application-loop owner;
- a shared bounded particle/effect owner;
- a standard Activity-local progress/event adapter pattern;
- a reusable reference-canvas static-backdrop presentation helper.

Do **not** extract those globally merely because one Activity now has them. First look for the same need in at least one or two additional Activities and compare semantics.

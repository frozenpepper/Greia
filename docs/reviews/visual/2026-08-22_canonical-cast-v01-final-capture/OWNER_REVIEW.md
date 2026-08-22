# Owner Review — Canonical Cast v0.1 Final Capture Integrity

**Date:** 2026-08-22  
**Disposition:** **ACCEPTED — CANONICAL CAST v0.1 SIMULATOR RUNTIME GATE CLOSED**  
**Evidence class:** `SIMULATOR VISUAL REVIEW`  
**Reviewed bundle:** `GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_FINAL_CAPTURE_2026-08-22.zip`  
**Implementation/evidence baseline:** `a4381eb9049ef4be7860352535588d078111848e`

## 1. Owner conclusion

The final capture-integrity pass resolves the evidence defects that blocked acceptance of the earlier canonical-cast runtime submissions.

The six-character canonical family is accepted at **Activity Simulator runtime scope**:

```text
Lilli
Leo
Flash
Dani
Tito
Momo
```

The accepted runtime contract remains:

```text
5 semantic authored states
neutral / blink / happy / surprised / sleepy

6 shared semantic motions
idle_bounce / blink / happy_hop / celebrate_pop / surprised_wobble / sleepy_sway

build-time PNG renditions
+ bounded shared visual cache
+ bounded failed-rendition memory
+ whole-character fixed-size translation motion
+ neutral/default state fallback
```

No additional pure-art cast pass or another runtime-cast proof Activity is required before real Activity use.

## 2. Direct pixel review

The actual transferred PNGs were inspected rather than accepting the agent report alone.

### Clean ensemble

`01-full-fixture-normal.png` is now a genuine clean baseline:

- all six characters are visible;
- the developer fixture controls are present;
- `Req: default | Rendered: default | Fallback: NO` is visible;
- no fault-injection screen contaminates the capture;
- contact shadows remain grounded;
- the protected Home region is not obscured by fixture controls.

### Five-state family

`02-five-states.png` contains five clean 1024×600 rows for:

```text
neutral
blink
happy
surprised
sleepy
```

Each row visibly shows all six current characters and reports matching requested/rendered variants with no fallback. This is sufficient visual proof of the 6 × 5 state family at simulator scope.

### Motion/state pairing

The previous stale-state defects are corrected:

- `03-happy-hop.png` — Flash / `happy` / `happy_hop`;
- `04-surprised-wobble.png` — Dani / `surprised` / `surprised_wobble`, with the authored surprised face actually visible;
- `05-sleepy-sway.png` — Momo / `sleepy` / `sleepy_sway`, with the authored sleepy face actually visible.

The motion remains appropriately cheap and restrained. The screenshots do not imply skeletal animation, continuously resized surfaces, or per-frame rotations.

### Non-default fallback

`06-state-fallback.png` is now self-proving:

```text
requested state/variant = happy
rendered variant        = default
fallback                = YES (default)
```

Flash visibly renders the neutral/default art while the Activity remains alive.

This matches the bounded failed-rendition implementation in `PygameSceneRenderer`: corrupt/missing rendition keys are remembered through `BoundedCache`, successful fallback continues through the ordinary shared visual cache, and `renderer.clear()` resets the failure memory.

### Required default failure

`07-default-failure.png` now reaches the fixture's deliberate bounded `Activity Visual Safe Fallback Mode` surface instead of capturing the launcher `Starting...` transition. No Python traceback, terminal, Linux shell, or crash dialog is exposed.

One fixture-only diagnostic detail remains imperfect: the ordinary top diagnostic line is computed after the failed scene draw and still reports `Rendered: default | Fallback: NO` even while the explicit required-failure card is visible. The failure card plus structured simulator trace are unambiguous, so this does **not** block runtime acceptance. If this developer fixture is touched again, the hard-failure diagnostic should report `Rendered: none` / required failure rather than the pre-failure default expectation. Do not spend another acceptance cycle solely on that developer-only label.

### Responsive proof

The previous relabeling problem is corrected:

- `08-resp-1024x600-normal.png` visibly reports `UI: NORMAL` and `Screen: 1024x600`;
- `09-resp-1024x600-large.png` visibly reports `UI: LARGE` and `Screen: 1024x600`;
- `10-resp-1366x768-compact.png` is actually 1366×768 and visibly reports `UI: COMPACT`, `Canvas: 1024x600`, `Screen: 1366x768`.

The contained reference-canvas behavior is therefore accepted for this fixture at simulator scope.

## 3. Evidence/provenance review

`simulator-trace.json` now has one structured record per final capture and separates Phase A, B, and C. Records contain Activity ID, process/session identity, state, motion, viewport, interface size, requested/rendered variant, fault target, and fallback expectation/observation.

The initial committed `runtime-audit.json` omitted several fields required by the final gate even though the underlying evidence was present. The owner review corrected the committed audit rather than requiring another simulator run. The corrected audit records:

- canonical source root `assets/visual/characters/canonical/v0.1/`;
- six current semantic IDs;
- five semantic states and neutral=`default` runtime mapping;
- 30 generated runtime PNGs;
- bounded negative-cache owner and limit (`64`);
- exact reported build/test commands/results;
- simulator evidence classification.

This documentary correction does not alter runtime evidence.

## 4. Acceptance boundary

Accepted:

- canonical six-character source family v0.1;
- 30 build-time runtime character renditions;
- renderer-neutral semantic state/motion vocabulary;
- Pygame realization through the existing scene/shared-visual path;
- bounded failed-rendition memory;
- non-default state fallback to neutral/default;
- deliberate Activity-level safe behavior when a required default cannot render;
- final responsive/provenance evidence through the real Activity Simulator.

Not claimed:

- physical Acer/Pi performance acceptance;
- Web/HTML character renderer parity;
- any `lead_character` / `supporting_characters` package schema;
- exclusive character ownership of Collections or Activity categories;
- skeletal/body-part animation.

## 5. Next workstream decision

Do **not** add character metadata merely because it was once listed as a possible follow-up.

The next useful visual milestone is a real first-party Activity-authoring exercise using the system as an Activity author would:

```text
visual-needs inventory
→ generic authoring-library discovery helper
→ preferred/candidate-reference selection
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL decisions
→ canonical character use only where it genuinely helps
→ Activity-local final art where needed
→ existing Greia runtime/scene/UI integration
→ real Activity Simulator pixel review
```

Use an existing Activity rather than another proof-only fixture. `Shape Garden` is the preferred exercise because it already exposes the first Activity semantic visual seam, belongs to both `create` and `learn`, and currently has intentionally minimal visual presentation that can demonstrate whether the authoring toolbox produces a meaningful real-product improvement without changing its educational mechanics.

This exercise should determine organically whether lead/supporting-character metadata is actually useful later.

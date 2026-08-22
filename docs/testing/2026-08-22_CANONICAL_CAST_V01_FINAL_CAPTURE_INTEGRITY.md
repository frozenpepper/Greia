# Canonical Cast v0.1 — Final Capture Integrity Gate

**Status:** EXECUTE  
**Date:** 2026-08-22  
**Owner review:** `docs/reviews/visual/2026-08-22_canonical-cast-v01-runtime-recheck/OWNER_REVIEW_CAPTURE_INTEGRITY.md`  
**Implementation baseline:** `f1a9afe85c4fb6bd4a15d2bbea5c40835a8891ee`  
**Evidence class if accepted:** `SIMULATOR VISUAL REVIEW`

## 1. Goal

Close the canonical cast v0.1 runtime/simulator gate with one **strictly isolated, self-validating capture pass**.

This gate is not an art redesign and not a broad runtime rewrite. Preserve the accepted six-character art, promoted source family, 30 build-time PNG renditions, semantic states/motions, and the bounded failed-rendition memory unless this pass exposes a concrete implementation defect.

The problem to solve is evidence integrity:

- no fault-injection contamination of normal captures;
- no screenshots taken before the intended state is actually visible;
- no filename/status mismatch;
- no responsive label without proof of the real interface-size setting;
- no fallback claim based only on a filename or loose trace note.

## 2. Hard boundaries

Do not:

- redraw Lilli, Leo, Flash, Dani, Tito, or Momo;
- create another character state or motion vocabulary;
- add skeletal/body-part animation;
- introduce another renderer, asset loader, or cache;
- add shipping child-facing diagnostics;
- implement Activity `lead_character` / `supporting_characters` metadata;
- start Generic Batch B or another art-production tranche;
- claim physical Acer/Pi evidence;
- query or run GitHub Actions.

Test-only diagnostic UI inside `tests/fixtures/activities/canonical_cast_showcase/` is allowed where required to make the evidence self-proving.

## 3. Start from a provably clean baseline

Work on canonical `main`.

Before any capture:

```bash
git status --short
git branch --show-current
git pull --ff-only origin main

command -v rsvg-convert
make visual-assets
make visual-assets-check
pytest tests/test_scene*.py tests/test_visual*.py
```

Use a new isolated simulator state and a new project-local evidence directory. Do not reuse the prior recheck state or prior screenshots.

Example naming only; adapt to the existing documented simulator workflow if required:

```text
GREIA_SIMULATOR_STATE = fresh state dedicated to final capture integrity
tmp/canonical-cast-v01-final-capture/
```

Before Phase A begins, explicitly verify that the generated character PNGs under:

`assets/visual/runtime/v1/characters/`

match the freshly generated catalogue and that **no intentional corruption is active**.

## 4. Evidence instrumentation — developer fixture only

Inspect the current showcase fixture and add only the minimum developer-only diagnostic readout required for self-validating captures.

The fixture surface must visibly expose enough information to prove the requested scenario. At minimum include:

```text
selected character id
semantic state
semantic motion
actual interface-size category
actual simulator/outer viewport size when available to the Activity/test harness
reference canvas size
requested rendition variant
rendered rendition variant
fallback used: yes/no
```

If the renderer currently does not expose the rendered/fallback outcome in a renderer-neutral way, implement the narrowest testable mechanism that preserves the existing architecture. Do not create a second image path merely to produce diagnostics.

Normal child Activities must remain unaffected.

The top-left protected Home region must remain clear except for Greia's own system control.

## 5. Mandatory scenario isolation

Execute the capture work in **three isolated phases**. Rebuild/restore generated assets and use a fresh simulator process/state between fault-injection phases.

### Phase A — clean normal evidence

Before this phase:

1. run `make visual-assets`;
2. run `make visual-assets-check`;
3. confirm `flash_happy.png`, `dani_neutral.png`, and all other generated character PNGs are healthy;
4. start a fresh simulator state;
5. load `tests/fixtures/activities/canonical_cast_showcase/` through the canonical Simulator Activity-folder workflow, not by executing `main.py` directly.

Only after all Phase A captures are complete may any PNG be disturbed.

Create:

```text
01-full-fixture-normal.png
02-five-states.png
03-happy-hop.png
04-surprised-wobble.png
05-sleepy-sway.png
08-resp-1024x600-normal.png
09-resp-1024x600-large.png
10-resp-1366x768-compact.png
```

### Phase B — isolated non-default fallback

Before this phase:

1. stop the Phase A simulator;
2. run `make visual-assets` and `make visual-assets-check` again;
3. create a fresh simulator state;
4. deliberately corrupt/move **only** `assets/visual/runtime/v1/characters/flash_happy.png` (or another explicitly documented non-default target if source reality requires it);
5. launch the fixture cold through the real Simulator;
6. request Flash / happy in a static or otherwise unambiguous motion state.

Capture only:

`06-state-fallback.png`

Then stop the simulator and immediately restore generated assets with:

```bash
make visual-assets
make visual-assets-check
```

Do not proceed until restoration passes.

### Phase C — isolated required-default failure

Before this phase:

1. start from freshly rebuilt/validated assets;
2. create another fresh simulator state;
3. deliberately corrupt/move **only** `assets/visual/runtime/v1/characters/dani_neutral.png`;
4. launch cold through the real Simulator;
5. explicitly select Dani / neutral / static;
6. wait until the Activity itself reaches its deliberate required-visual safe fallback surface.

Capture only:

`07-default-failure.png`

Do **not** capture the launcher `Starting...` transition.

Then stop and restore immediately:

```bash
make visual-assets
make visual-assets-check
```

## 6. Pre-capture rule — visible state must match filename

Before **every** screenshot, inspect the actual fixture status/debug readout. If it does not match the scenario named below, do not capture.

The screenshot itself must carry enough visible information to let an owner verify the scenario without trusting its filename.

## 7. Exact image acceptance contracts

### 7.1 `01-full-fixture-normal.png`

Must show:

- real full showcase fixture UI;
- six visible current characters;
- no error/fallback box;
- no loading/Starting screen;
- selected/current status visible;
- clean ensemble composition;
- system Home area unobstructed.

### 7.2 `02-five-states.png`

Create a composite from five **clean Phase A** captures only:

```text
neutral
blink
happy
surprised
sleepy
```

Each row must show all six current characters resolving the same semantic state.

No row may show an Activity fallback, launcher loading surface, corrupt asset, or stale status.

The composite must therefore prove the visible 6 × 5 family rather than merely list the intended 30 combinations in JSON.

### 7.3 `03-happy-hop.png`

Visible status must prove:

```text
character.flash
state = happy
motion = happy_hop
fallback used = no
```

Capture at a useful mid-hop moment with grounded contact shadow behavior visible.

### 7.4 `04-surprised-wobble.png`

Visible status must prove:

```text
character.dani
state = surprised
motion = surprised_wobble
fallback used = no
```

Dani's authored surprised face must actually be visible. Do not accept `state = happy` with wobble motion.

### 7.5 `05-sleepy-sway.png`

Visible status must prove:

```text
character.momo
state = sleepy
motion = sleepy_sway
fallback used = no
```

Momo's authored sleepy face must actually be visible. Do not accept `state = happy` with sway motion.

### 7.6 `06-state-fallback.png`

This must be a self-proving developer capture of the isolated Phase B fault.

Visible diagnostic state must prove conceptually:

```text
character.flash
requested semantic state = happy
requested rendition = happy
rendered rendition = default
fallback used = yes
Activity alive = yes
```

The image must show Flash rendered as the neutral/default art rather than merely relying on the trace filename.

The automated regression for failed-rendition memory must also prove that repeated draws do not retry the corrupt non-default rendition every frame.

### 7.7 `07-default-failure.png`

Must show the **Activity's deliberate safe fallback surface** after a cold Dani/default failure.

It must not show:

- `Starting...`;
- launcher transition UI;
- Python traceback;
- shell/terminal/error dialog.

The visible message may be developer-oriented because this is a fixture, but must remain bounded and deliberate.

### 7.8 `08-resp-1024x600-normal.png`

Must visibly/traceably prove:

```text
outer viewport = 1024x600
interface size = normal
```

Use a meaningful hero/ensemble configuration and confirm no clipping or non-uniform character stretch.

### 7.9 `09-resp-1024x600-large.png`

Must visibly/traceably prove:

```text
outer viewport = 1024x600
interface size = large
```

The fixture's visible status must report `LARGE`, not `NORMAL`.

If the simulator cannot actually set the interface-size category through its supported settings path, stop and report the product/tooling blocker rather than relabeling a normal screenshot as large.

### 7.10 `10-resp-1366x768-compact.png`

Must visibly/traceably prove:

```text
outer viewport = 1366x768
interface size = compact
reference canvas = 1024x600 containment (if that remains the actual design)
```

If the remote screenshot endpoint intentionally exports only the contained 1024×600 child/reference surface, that is acceptable only when the trace and visible status independently prove the 1366×768 outer viewport and COMPACT setting. Do not claim the PNG's dimensions themselves are the outer viewport if they are not.

## 8. Automated failed-rendition regression

Preserve or strengthen the bounded negative-cache tests.

At minimum prove:

1. first draw requests corrupt `happy` and then `default`;
2. repeated draw does **not** request corrupt `happy` again while the failed-rendition memory remains valid;
3. successful `default` continues to render;
4. failed required `default` is not repeatedly decoded every frame;
5. `renderer.clear()` resets the failed-rendition memory, after which the rendition can be attempted again;
6. the failed-rendition memory remains hard-bounded.

Use existing `BoundedCache`; do not invent another cache abstraction.

## 9. Structured simulator trace

Replace/extend the loose action-only trace so each screenshot has a structured evidence record.

For every capture record at least:

```text
file
scenario_id
simulator_session_id or pid
Activity id/source folder
selected_character
semantic_state
semantic_motion
outer_viewport
interface_size
reference_canvas
requested_variant
rendered_variant
fault_injection_active
fault_target
fallback_expected
fallback_observed
capture_timestamp
```

Raw key/click events may remain as supplementary trace data, but they are not sufficient by themselves.

The trace must clearly separate Phase A, B, and C sessions.

## 10. Runtime audit correction

Produce a corrected `runtime-audit.json` grounded in current repository/source truth.

It must accurately record:

- stable canonical source root: `assets/visual/characters/canonical/v0.1/`;
- six current IDs exactly as defined in `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`;
- five semantic states and runtime neutral=`default` mapping;
- 30 generated runtime PNGs;
- exact build/test commands and exact result counts;
- negative-cache implementation and bounds;
- each fault target, when it was disturbed, and when restoration passed;
- actual simulator viewport/interface settings for every responsive capture;
- exact evidence filenames;
- evidence classification.

Do not invent role descriptions or paths that differ from the canonical cast/system documents.

## 11. Owner review package

Create a **new** root-level uncommitted ZIP:

`GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_FINAL_CAPTURE_2026-08-22.zip`

Include only:

```text
OWNER_FINAL_RECHECK.md
runtime-audit.json
simulator-trace.json
01-full-fixture-normal.png
02-five-states.png
03-happy-hop.png
04-surprised-wobble.png
05-sleepy-sway.png
06-state-fallback.png
07-default-failure.png
08-resp-1024x600-normal.png
09-resp-1024x600-large.png
10-resp-1366x768-compact.png
```

Do not include promoted source files, runtime PNG inventories, logs unrelated to the acceptance decision, or prior contaminated screenshots.

Commit the corresponding curated review directory under:

`docs/reviews/visual/2026-08-22_canonical-cast-v01-final-capture/`

## 12. Stop conditions

Stop and report instead of improvising if any of the following occurs:

- any Phase A capture shows fallback/loading/fault contamination;
- visible state/motion does not match the intended filename;
- a fault-injected PNG remains disturbed when moving between phases;
- the required-default screenshot cannot be captured after the Activity itself reaches its fallback surface;
- the simulator cannot truly apply the requested `large` or `compact` interface-size setting;
- the trace cannot distinguish outer viewport from contained child/reference surface;
- making fallback evidence self-proving would require a second production renderer/asset path;
- the final asset restoration fails `make visual-assets-check`.

Preserve failure evidence and record the exact blocker rather than writing a PASS narrative.

## 13. Documentation and completion discipline

Do not rewrite the earlier owner reviews or contaminated recheck history.

If this gate passes, append/update living continuation documents to state that the final capture-integrity pass closed canonical cast v0.1 simulator runtime acceptance.

If it fails, record the specific unresolved blocker and keep this gate active.

Do not advance to lead/support character metadata or another art tranche before owner review of the final ZIP.

## 14. Git completion

Before committing:

```bash
git status --short
make visual-assets
make visual-assets-check
pytest tests/test_scene*.py tests/test_visual*.py
git status --short
```

Then commit coherent source/test/docs/evidence changes on `main`, pull/rebase, and push without force.

Return only the concise completion summary plus:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_FINAL_CAPTURE_2026-08-22.zip
```

The next owner decision will be based on that ZIP, not on a prose claim of PASS.

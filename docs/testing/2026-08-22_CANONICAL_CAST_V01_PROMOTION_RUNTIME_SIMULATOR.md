# Canonical Cast v0.1 — Promotion, Runtime Integration, and Activity Simulator Gate

**Status:** EXECUTE  
**Date:** 2026-08-22  
**Owner art authority:** `docs/reviews/visual/2026-08-22_flash-white-rabbit-identity-revision/PRIMARY_REVIEW.md`  
**Cast system:** `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`  
**Character grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Motion vocabulary:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`  
**Simulator:** ADR 0029 + `docs/development/GREIA_ACTIVITY_SIMULATOR.md`  
**Visual evidence contract:** `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`  
**Evidence class if accepted:** `SIMULATOR VISUAL REVIEW`

## 1. Goal

Move the owner-accepted six-character cast from candidate source art into Greia's real shared visual/runtime path and prove the result through the **real Greia Activity Simulator**.

This gate owns exactly:

1. stable source promotion for the accepted six characters;
2. explicit current-identity migration from historical Nino to Leo without destroying provenance;
3. build-time PNG rendition selection for all six characters and five states;
4. minimal renderer-neutral semantic character state/motion support;
5. one small developer-only Activity fixture that exercises the real Activity/Shell/runtime path;
6. fail-soft, responsive and visual acceptance through the Activity Simulator;
7. curated evidence for owner inspection.

This is **not** another art-design gate.

## 2. Accepted source lineup — do not improvise

Use exactly these reviewed sources.

### Lilli

Source root:

`assets/visual/pack_candidates/canonical_characters/2026-08-22/lilli/`

### Leo

Source root:

`assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/leo/`

### Flash

Use the **white-rabbit revision**, not the earlier raspberry candidate:

`assets/visual/pack_candidates/flash_identity_revision/2026-08-22/flash/`

### Dani

Source root:

`assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/dani/`

### Tito

Source root:

`assets/visual/pack_candidates/canonical_characters/2026-08-22/tito/`

### Momo

Source root:

`assets/visual/pack_candidates/canonical_characters/2026-08-22/momo/`

Every accepted character has these complete source states:

```text
neutral.svg
blink.svg
happy.svg
surprised.svg
sleepy.svg
```

Do not redraw any of them during this gate.

## 3. Stable source promotion

Create:

```text
assets/visual/characters/canonical/v0.1/
  catalog.toml
  README.md
  MOTION.md
  lilli/
  leo/
  flash/
  dani/
  tito/
  momo/
```

For each character copy the accepted:

- `source_master.svg`;
- five complete state SVGs;
- reviewed authoring components that exist in the source candidate.

The promoted source catalogue must use current semantic IDs:

```text
character.lilli
character.leo
character.flash
character.dani
character.tito
character.momo
```

The catalogue must record source provenance for each character so the origin of the promoted files is explicit.

### Nino provenance rule

Do **not** delete or rename historical Nino evidence/candidate source.

Current product identity is Leo. Historical `character.nino` remains provenance only.

Update living source/catalogue documentation so future work does not accidentally treat Nino as a seventh current cast member.

Do not add a silent runtime alias `character.nino -> character.leo` unless an existing shipped consumer demonstrably requires compatibility. If such a consumer exists, document it and implement the narrowest compatibility mapping possible. Otherwise, current runtime IDs should simply use `character.leo`.

## 4. Source-library catalogue

Update `assets/visual/library/catalog.toml` to describe the **current six-character source family** rather than the obsolete four-character seed.

Requirements:

- six current identities only;
- five states per identity;
- source paths point at `assets/visual/characters/canonical/v0.1/`;
- historical Nino provenance is documented, not exposed as an ordinary current cast entry;
- keep source-library/runtime-selection boundaries clear.

Do not turn this file into a second runtime catalogue.

## 5. Build-time runtime renditions

Update:

`assets/catalog/shared_visuals_v1_source.toml`

Add all six canonical character semantic IDs through the existing explicit build-time rendition system.

For each character use these runtime variants:

```text
default      # source neutral.svg
blink
happy
surprised
sleepy
```

The external semantic state is `neutral`; the existing runtime variant name `default` remains the neutral rendition for compatibility with `SceneActorDefinition` and the shared visual catalogue.

Each generated rendition should remain a fixed **256×256** PNG unless existing build constraints require a documented different size.

Expected output family:

```text
assets/visual/runtime/v1/characters/
  lilli_neutral.png
  lilli_blink.png
  lilli_happy.png
  lilli_surprised.png
  lilli_sleepy.png
  leo_neutral.png
  ...
  momo_sleepy.png
```

Do not rasterize SVG at normal Activity runtime.

Run as build prerequisites:

```bash
command -v rsvg-convert
make visual-assets
make visual-assets-check
```

These are prerequisite/build checks only. They are **not** visual acceptance.

## 6. Renderer-neutral semantic state contract

Inspect current:

```text
src/greia_platform/scene_actor.py
tests/test_scene_actor.py
src/greia_platform/scene.py
src/greia_platform/pygame_scene.py
```

Preserve existing source compatibility where practical.

The resulting renderer-neutral character API must support the semantic states:

```text
neutral
blink
happy
surprised
sleepy
```

and shared motion names:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

### 6.1 Keep motion cheap

For this first runtime implementation, motion should use:

- state swaps;
- fixed-size whole-character x/y translation;
- bounded timing/amplitude;
- existing grounded contact shadow.

Do **not** implement continuous per-frame raster size changes merely to create squash/stretch. That would churn the bounded surface cache because the current cache key includes requested size.

Do **not** implement continuous per-frame Pygame rotation allocations merely to mimic storyboard angles.

A semantic `surprised_wobble` may be represented by small horizontal recoil/settle translation rather than literal rotation. A `sleepy_sway` may use a tiny horizontal sway. The runtime vocabulary is semantic; it does not need to reproduce every storyboard transform mechanically.

### 6.2 Expected motion/state relationship

A clean implementation should behave conceptually like:

```text
idle_bounce       -> neutral, with existing periodic authored blink + tiny vertical life
blink             -> blink state, brief, then settle
happy_hop         -> happy state + bounded vertical hop
celebrate_pop     -> happy state + larger bounded vertical pop
surprised_wobble  -> surprised state + small horizontal recoil/wobble
sleepy_sway       -> sleepy state + slow small horizontal sway
```

The exact public types/signatures may follow existing project style, but avoid stringly procedural sprawl. A small enum/value-object vocabulary is preferred if it simplifies validation and tests.

### 6.3 Character personality variation

Allow small per-actor motion intensity/timing variation without creating per-character animation engines.

One bounded scalar or similarly small configuration mechanism is enough.

Do not add dozens of per-motion tuning fields merely because six characters exist.

## 7. Variant fail-soft behavior

The state system must fail softly without inventing a second renderer.

Target behavior:

1. if a requested non-default state rendition is unavailable/corrupt, fall back once to that actor's `default` neutral rendition;
2. if the default required character rendition also cannot render, the containing Activity may use its deliberate local fallback or omit the actor, but must not expose Linux/Python errors to the child;
3. avoid retrying a known corrupt optional/state rendition every frame.

Implement this through the existing scene/shared-visual path, not a character-specific parallel image loader.

A narrow general scene-node fallback-variant mechanism is acceptable if it is cleaner than special-casing character IDs and remains bounded/tested.

## 8. Automated tests

At minimum expand/add focused tests covering:

```text
tests/test_scene_actor.py
```

and the relevant asset/rendition tests.

Required test coverage:

- all accepted state names map to expected variants;
- neutral maps to runtime `default`;
- invalid semantic states/motions are rejected or fail deterministically according to the chosen typed API;
- existing idle/blink behavior remains compatible;
- `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway` move the actor without changing shadow geometry unexpectedly;
- motion never produces negative/zero body dimensions;
- sampling is deterministic for the same inputs;
- fallback from a missing non-default variant to neutral/default is bounded;
- all six character IDs and all five runtime variants exist in the generated catalogue;
- source promotion catalogue has no duplicate current IDs and contains no current Nino entry.

Run the narrow focused tests first. Run broader project tests required by touched modules afterward.

Do not claim simulator acceptance from pytest.

## 9. Developer-only Activity Simulator fixture

Create a **developer/test fixture Activity**, not a new shipped child Activity.

Preferred location:

```text
tests/fixtures/activities/canonical_cast_showcase/
```

It must be a structurally valid Greia Python Activity that can be loaded through the simulator's normal **Load Activity Folder…** workflow.

It must consume the real Greia semantic visual/scene actor path. Do not read the promoted SVG files directly and do not load generated PNG paths manually.

### Fixture behavior

The fixture should provide a simple developer-oriented showcase with:

- all six characters visible together;
- clear current selected actor;
- controls to choose all five semantic states;
- controls to trigger all six semantic motions;
- one mode showing the full ensemble together;
- one mode showing a selected character large enough to inspect expression/motion;
- a small on-screen state/motion label is acceptable because this is developer tooling, not a child-shipping Activity.

Use normal Greia canvas/responsive/system-safe primitives. Do not branch on simulator identity.

Keep the fixture small and readable. It is a runtime acceptance harness, not a new UI product.

## 10. Preparation for simulator acceptance

From repository root:

```bash
git status --short
git branch --show-current
git pull --ff-only origin main

export GREIA_SIMULATOR_HEADLESS=1
export GREIA_SIMULATOR_STATE="$HOME/.greia-simulator-canonical-cast-v01"
rm -rf "$GREIA_SIMULATOR_STATE"
rm -rf tmp/canonical-cast-v01-evidence
mkdir -p tmp/canonical-cast-v01-evidence

command -v rsvg-convert
make visual-assets
make visual-assets-check
```

Start the real simulator:

```bash
python3 tools/greia_simulator.py --state-dir "$GREIA_SIMULATOR_STATE"
```

Use the loopback bridge/CLI documented in `docs/development/GREIA_ACTIVITY_SIMULATOR.md`:

```text
http://127.0.0.1:8767
python3 tools/greia_simulator_ctl.py status
python3 tools/greia_simulator_ctl.py screenshot <path.png>
python3 tools/greia_simulator_ctl.py key <KEY>
python3 tools/greia_simulator_ctl.py click <X> <Y>
```

Load the fixture through **Load Activity Folder…**. Do not launch its Python file directly as acceptance evidence.

## 11. Mandatory simulator acceptance matrix

### 11.1 Six-cast neutral ensemble — 1024×600 normal

Show all six current characters:

```text
Lilli  Leo  Flash  Dani  Tito  Momo
```

Verify:

- current IDs resolve through the real generated runtime catalogue;
- no Nino appears as a current cast member;
- Flash is the accepted white/coral/bolt version;
- character aspect ratios are preserved;
- no actor is stretched/cropped accidentally;
- faces remain readable;
- contact shadows remain grounded;
- fixture UI does not collide with protected system-safe regions.

Capture raw:

`tmp/canonical-cast-v01-evidence/01-ensemble-1024x600.png`

### 11.2 State proof

Exercise each semantic state at least once through runtime selection.

Capture one selected character in:

- neutral;
- blink;
- happy;
- surprised;
- sleepy.

Also verify by interaction/log/audit that every one of the 30 character/state combinations resolves successfully.

Capture:

`tmp/canonical-cast-v01-evidence/02-five-states.png`

### 11.3 Motion proof

Exercise:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Capture at least:

- mid `happy_hop`;
- mid `surprised_wobble`;
- mid `sleepy_sway`.

Verify the contact shadow remains grounded and motion is subtle/character-like rather than camera-like.

Capture:

```text
tmp/canonical-cast-v01-evidence/03-happy-hop.png
tmp/canonical-cast-v01-evidence/04-surprised-wobble.png
tmp/canonical-cast-v01-evidence/05-sleepy-sway.png
```

### 11.4 Non-default state fallback

Temporarily corrupt or move one generated **non-default** character state PNG, for example:

`assets/visual/runtime/v1/characters/flash_happy.png`

Restart the isolated simulator and request Flash `happy` through the fixture.

Verify:

- the Activity remains alive;
- Flash falls back to neutral/default rather than disappearing/crashing;
- no Linux/Python error is exposed to the child surface;
- there is no repeated per-frame exception/decode storm.

Capture:

`tmp/canonical-cast-v01-evidence/10-state-fallback.png`

Restore with:

```bash
make visual-assets
make visual-assets-check
```

### 11.5 Default rendition failure

Temporarily corrupt/move one default character PNG, for example:

`assets/visual/runtime/v1/characters/dani_neutral.png`

Exercise the fixture.

Verify its deliberate Activity-level fallback/omission keeps the Activity usable and does not expose a traceback.

Capture:

`tmp/canonical-cast-v01-evidence/11-default-fallback.png`

Restore generated assets immediately afterward.

### 11.6 Motion disabled

Exercise the same ensemble with motion disabled.

Verify all characters still form a complete, intentional static composition and state selection still works.

Capture:

`tmp/canonical-cast-v01-evidence/12-motion-disabled.png`

## 12. Responsive matrix — mandatory

Exercise through the Activity Simulator at:

| Row | Viewport | Interface size |
|---|---:|---|
| 1 | 1024×600 | normal |
| 2 | 1024×600 | large |
| 3 | 1280×800 | normal |
| 4 | 1366×768 | compact |
| 5 | 1920×1080 | normal |
| 6 | 1111×700 | normal |

For every row verify actual pixels:

- all six are reachable/visible in ensemble mode;
- selected-character mode remains readable;
- no non-uniform character stretching;
- no clipped labels/controls in the fixture;
- system-safe Home/Back area remains respected;
- 64-ish icon/world-size character use remains legible where exercised;
- no viewport-specific art fork was introduced.

Store raw screenshots under:

`tmp/canonical-cast-v01-evidence/20-...`

## 13. Cache/frame sanity

After character surfaces are warm, observe at least 10 seconds in ensemble + motion modes.

Verify:

- visual cache remains bounded;
- repeated motion does not continuously create new raster sizes;
- requested fixed character sizes settle into a finite cache working set;
- no frame/resource runaway is observed in simulator scope.

Record simulator frame/status data, but do **not** convert this into a physical Acer/Pi performance claim.

## 14. Curated committed owner evidence

Create:

`docs/reviews/visual/2026-08-22_canonical-cast-v01-runtime-simulator/`

Commit **8–10 curated PNGs**, not every raw capture.

Required semantic set:

```text
01-ensemble.png
02-five-states.png
03-happy-hop.png
04-surprised-wobble.png
05-sleepy-sway.png
06-constrained.png
07-large.png
08-state-fallback.png
09-default-fallback.png
10-motion-disabled.png          # optional if another sheet cleanly proves it
```

Also commit:

```text
REVIEW.md
runtime-audit.json
```

`runtime-audit.json` must record:

- promoted source path and six IDs;
- 30 source-state files;
- 30 generated runtime variants;
- generated catalogue IDs/variants;
- test commands/results;
- responsive matrix rows;
- fallback assets intentionally disturbed/restored;
- cache/frame observations;
- evidence classification.

## 15. Owner transfer ZIP

Create at project root and **do not commit**:

`GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_RUNTIME_SIMULATOR_2026-08-22.zip`

Include only the curated PNGs, `REVIEW.md`, and `runtime-audit.json`.

Final response must include exactly:

`VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_RUNTIME_SIMULATOR_2026-08-22.zip`

## 16. Documentation updates when complete

Update the living authorities to reflect actual evidence, not hoped-for PASS:

```text
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

If simulator acceptance fails, record it as incomplete and preserve the evidence instead of writing an optimistic completion statement.

## 17. Explicitly out of scope

Do **not** in this gate:

- redesign any of the six characters;
- create a seventh mascot;
- implement skeletal/bone animation;
- implement runtime limb composition;
- create new generic art Batch B;
- add six new Home Collections;
- implement optional Activity `lead_character`/`supporting_characters` manifest fields yet;
- modify package trust/permissions/progression based on characters;
- claim physical Acer/Pi acceptance;
- claim Web character runtime support;
- close/reorder R7.

## 18. Stop conditions

Stop and report rather than improvising if:

- any accepted source state is missing;
- the promoted source copy does not byte/visually correspond to the accepted candidate;
- build-time rendition generation requires runtime SVG rasterization;
- state fallback would require a parallel asset loader/cache;
- motion semantics require continuously varying raster dimensions to work;
- the developer fixture cannot be loaded through the canonical Activity Simulator source-loader path;
- fallback testing leaves generated assets unrestored;
- the simulator exposes a traceback/Linux shell to the child surface.

## 19. Git completion

Work directly on canonical `main`.

Do not query/use GitHub Actions.

Before final commit:

```bash
git status --short
make visual-assets
make visual-assets-check
# focused tests + required broader touched-module tests
git status --short
```

Then:

```bash
git add -A
git commit -m "feat(visual): promote canonical cast v0.1 and integrate semantic runtime motion"
git pull --rebase origin main
git push origin main
git rev-parse HEAD
```

Do not force-push.

Return:

- final pushed SHA;
- stable canonical source path;
- six current IDs;
- generated 30-state runtime inventory summary;
- source/build test results;
- simulator responsive/fallback result matrix;
- committed evidence directory;
- owner ZIP path;
- explicit statement of what remains unproven.
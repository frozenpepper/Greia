# Canonical Cast v0.1 — Runtime Acceptance Recheck

**Status:** EXECUTE  
**Date:** 2026-08-22  
**Owner review:** `docs/reviews/visual/2026-08-22_canonical-cast-v01-runtime-simulator/OWNER_REVIEW.md`  
**Candidate implementation:** `0ed5eba13f2edcfd62f1c4204311da1baa1dab46`  
**Original gate:** `docs/testing/2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md`  
**Evidence class if this recheck passes:** `SIMULATOR VISUAL REVIEW`

## 1. Purpose

Do **not** redo the canonical cast promotion. The six-character source family and 30 runtime renditions are already useful implementation work.

This is a focused correction/recheck for four things that the first execution did not prove correctly:

1. bounded negative memory for a failed state rendition so a corrupt non-default PNG is not retried every frame;
2. a genuine cold default-rendition failure path;
3. actual Activity Simulator provenance for screenshots/interaction rather than scene-only evidence;
4. synchronization of living visual documentation after the real result is known.

No pure-art changes are authorized.

## 2. Preserve these accepted facts

Do not change unless a concrete implementation defect forces it:

```text
character.lilli
character.leo
character.flash
character.dani
character.tito
character.momo
```

Source root:

`assets/visual/characters/canonical/v0.1/`

States:

```text
neutral
blink
happy
surprised
sleepy
```

Motions:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Runtime remains:

- explicit build-time PNG renditions;
- fixed-size state swaps;
- cheap whole-character x/y translation;
- grounded contact shadow;
- existing shared visual catalogue/cache/scene path;
- no runtime SVG rasterization;
- no skeletal/body-part animation system.

## 3. First inspect current state

From repository root:

```bash
git status --short
git branch --show-current
git pull --ff-only origin main
git rev-parse HEAD
```

Read:

```text
AGENTS.md
docs/reviews/visual/2026-08-22_canonical-cast-v01-runtime-simulator/OWNER_REVIEW.md
docs/testing/2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md
src/greia_platform/scene_actor.py
src/greia_platform/scene.py
src/greia_platform/pygame_scene.py
src/greia_platform/pygame_visual_assets.py
src/greia_platform/ui_core.py
tests/test_scene_actor.py
tests/fixtures/activities/canonical_cast_showcase/main.py
docs/development/GREIA_ACTIVITY_SIMULATOR.md
```

Do not use or inspect GitHub Actions.

## 4. Fix failed-rendition retry behavior

### Problem

Current `PygameSceneRenderer.draw()` retries a requested failed primary rendition every frame before falling back to `fallback_variant`.

`PygameVisualSurfaceCache` caches successful surfaces only, so a corrupt PNG can repeatedly hit disk/decode/error handling.

### Required behavior

Add one small **bounded** renderer-level memory for known failed rendition requests.

A clean solution should key failure memory by at least:

```text
asset_id
variant
requested width
requested height
```

Requirements:

- use an existing bounded primitive such as `ui_core.BoundedCache` or an equivalently small bounded LRU;
- do not create an unbounded `set` of failed rendition keys;
- once a non-default requested rendition fails and its fallback succeeds, subsequent draws at the same key must skip the failed primary request and go directly to the fallback;
- a known failed required/default rendition must likewise avoid repeated disk/decode attempts if the containing Activity keeps drawing;
- `PygameSceneRenderer.clear()` must clear both successful visual surfaces and failed-rendition memory;
- do not move fallback logic into a character-only loader;
- do not negative-cache unrelated semantic IDs/variants globally across renderer instances;
- runtime assets are immutable during normal execution, so a renderer-lifetime failure memory is acceptable. A fresh renderer/restart or explicit `clear()` is the recovery boundary after repaired generated assets.

Keep the change small and OOP-consistent with the existing renderer/cache structure.

## 5. Automated regression tests

Expand the focused scene/renderer tests.

At minimum add explicit tests for:

### 5.1 Non-default fallback is not retried

Use a mock visual cache where:

```text
character.flash / happy   -> raises
character.flash / default -> succeeds
```

Draw the same scene at least 3 times.

Assert:

- every draw succeeds;
- `happy` is attempted exactly once for that rendition key;
- fallback/default is used after the first failure;
- no body dimensions change;
- no new character-specific loader exists.

### 5.2 Renderer clear resets failure memory

After the prior failure:

```python
renderer.clear()
```

Draw again and assert the primary rendition is attempted again once. This proves recovery is explicit and deterministic.

### 5.3 Required/default failure avoids repeated decode work

Use a mock cache where required `default` raises.

Draw/catch twice and assert the underlying failed rendition load is attempted once for that key even if `SceneRenderError` is raised again from remembered failure state.

### 5.4 Existing state/motion contract remains intact

Preserve/extend coverage that:

- all five semantic states map correctly;
- neutral maps to runtime `default`;
- all six motions remain deterministic;
- `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway` preserve body width/height and shadow geometry;
- invalid states/motions fail deterministically;
- all six IDs × five variants remain declared/generated.

Run the narrow tests first, then the broader touched visual/scene tests required by project convention.

## 6. Fix or prove fixture safe-area composition

The current fixture computes:

```python
viewport = activity_viewport_for_surface(screen)
safe_rect = viewport.safe_ui_rect()
```

but does not use `safe_rect`, while its control mapping is based on the full display size.

Inspect how the Simulator/Shell presents the child Activity surface.

Choose the narrow correct outcome:

### Outcome A — Activity surface already excludes protected system chrome

If the real Activity surface delivered to the process is already the correct system-safe drawing region, document/prove that from the actual simulator run and remove misleading unused imports/variables if appropriate.

### Outcome B — fixture must honor the safe viewport

If the Activity process receives an area that includes reserved/protected territory, refactor the **fixture only** to use the existing Greia viewport/reference-canvas conventions for its developer controls and scene.

Do not add simulator-only production behavior and do not modify protected navigation authority.

## 7. Build prerequisites

After code changes:

```bash
command -v rsvg-convert
make visual-assets
make visual-assets-check
```

Confirm all 30 generated character PNGs are restored and valid before the simulator run.

## 8. Fresh simulator state and evidence directory

Use a fresh isolated simulator state:

```bash
export GREIA_SIMULATOR_HEADLESS=1
export GREIA_SIMULATOR_STATE="$HOME/.greia-simulator-canonical-cast-v01-recheck"
rm -rf "$GREIA_SIMULATOR_STATE"
rm -rf tmp/canonical-cast-v01-recheck
mkdir -p tmp/canonical-cast-v01-recheck
```

Start the **real** simulator as documented in `docs/development/GREIA_ACTIVITY_SIMULATOR.md`.

Load:

`tests/fixtures/activities/canonical_cast_showcase/`

through the canonical **Load Activity Folder…** workflow. Do not run `main.py` directly for acceptance evidence.

Use only the documented loopback/CLI control path, for example:

```text
python3 tools/greia_simulator_ctl.py status
python3 tools/greia_simulator_ctl.py screenshot <path>
python3 tools/greia_simulator_ctl.py key <KEY>
python3 tools/greia_simulator_ctl.py click <X> <Y>
```

## 9. Prove simulator provenance before visual claims

Record a small machine-readable trace under:

`tmp/canonical-cast-v01-recheck/simulator-trace.json`

It must include enough information from the real simulator control/status surface to establish:

- simulator process/session started;
- loaded source folder is the canonical-cast showcase fixture;
- running Activity ID is `org.greia.fixture.canonical-cast-showcase`;
- viewport/interface-size setting for each screenshot row;
- exact screenshot output path;
- exact control actions used to select states/motions;
- no direct fixture Python launch was used.

Do not fabricate fields the control/status interface does not expose. Record the actual available identifiers/commands/results.

## 10. Genuine baseline screenshot

At 1024×600 / normal, capture the **full actual Activity surface** after the fixture is loaded:

`tmp/canonical-cast-v01-recheck/01-full-fixture-normal.png`

This image must visibly correspond to the committed fixture implementation. Unless the real Shell architecture deliberately clips them from the Activity surface, the fixture title/status/control UI should be visible.

Verify from actual pixels:

- six current characters are visible;
- no Nino current identity appears;
- Flash is the white/coral/gold version;
- no control overlaps protected Greia system navigation territory;
- state/motion controls are reachable;
- no traceback/Linux shell is visible.

If the screenshot still contains only the scene with none of the committed fixture UI, **stop** and explain the capture/runtime discrepancy before continuing.

## 11. State/motion interaction proof

Exercise all five states and all six motions through the running fixture.

Required captures:

```text
02-five-states.png
03-happy-hop.png
04-surprised-wobble.png
05-sleepy-sway.png
```

The trace must also record interaction/execution of:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Static screenshots need not individually capture every motion, but the trace must prove all six were selected through the real fixture.

## 12. Non-default failure recheck

### 12.1 Prepare cold failure

Stop/restart the isolated simulator/Activity so no successful `flash_happy` surface survives in memory.

Temporarily move/corrupt:

`assets/visual/runtime/v1/characters/flash_happy.png`

Load/reload the fixture, select Flash + `happy`, and capture:

`06-state-fallback.png`

Verify:

- Flash visibly falls back to neutral/default;
- Activity remains alive;
- no traceback/Linux error is exposed;
- instrumentation/test evidence confirms the failed `happy` load is not retried every frame.

Restore generated assets immediately after this subcase:

```bash
make visual-assets
make visual-assets-check
```

## 13. Genuine default-rendition failure recheck

Start from a **cold/restarted** renderer/simulator state.

Temporarily move/corrupt:

`assets/visual/runtime/v1/characters/dani_neutral.png`

Then explicitly select:

```text
actor: Dani
state: neutral
motion: none
```

This must actually request runtime variant `default`.

Capture:

`07-default-failure.png`

Required result:

- required Dani default rendition does not render;
- the fixture's deliberate Activity-level fallback/omission is visible;
- no Python traceback/Linux shell is exposed;
- no repeated disk/decode storm occurs after the first known failure;
- the screenshot must not simply show Dani happily rendered from another semantic state.

Restore immediately:

```bash
make visual-assets
make visual-assets-check
```

Restart/clear the renderer and verify Dani neutral renders normally again.

## 14. Responsive provenance recheck

Run at least these three deliberately distinct rows through the real simulator:

| Row | Viewport | Interface size |
|---|---:|---|
| A | 1024×600 | normal |
| B | 1024×600 | large |
| C | 1366×768 | compact |

Capture:

```text
08-resp-1024x600-normal.png
09-resp-1024x600-large.png
10-resp-1366x768-compact.png
```

Requirements:

- each trace entry records the actual row setting;
- normal and large captures must not be presented as separate proof if they are byte-identical because the interface setting was not actually applied;
- all six characters and fixture controls remain reachable/readable;
- system-safe navigation territory remains respected;
- no viewport-specific art fork exists.

If project policy still requires the original six-row matrix for closure, rerun all six. The three rows above are the minimum evidence correction; do not weaken an existing mandatory matrix without explicitly documenting why.

## 15. Cache/frame sanity with failure instrumentation

Observe at least 10 seconds after warm-up in a normal motion mode.

Record:

- surface cache max entries;
- observed surface working set;
- failed-rendition memory max entries;
- observed failed-rendition entries during fault injection;
- proof that successful motion does not create continuously varying raster sizes;
- proof that one corrupt non-default rendition is attempted once per rendition key, not once per frame.

This remains simulator evidence only. Do not claim physical Acer/Pi performance.

## 16. Documentation correction after the result is known

The first execution wrote an optimistic PASS while some living authorities remained stale.

After this recheck, update **all** required living docs coherently:

```text
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Required corrections include:

- `GREIA_ART_GRAPHICS_SYSTEM.md` must stop listing obsolete `Lilli / Nino / Tito / Momo` as the current cast and must point to the canonical-cast authority;
- the active visual-foundation plan's **Current checkpoint** and **Next exact action** must reflect the actual state rather than the already-completed generic-library admission gate;
- earlier progress/history remains append-only;
- if the recheck passes, mark canonical cast v0.1 runtime acceptance as **SIMULATOR VISUAL REVIEW**;
- if it fails, record the exact remaining blocker and do not retain optimistic PASS wording.

## 17. Correct owner review package

Create at project root and do **not** commit:

`GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_RUNTIME_RECHECK_2026-08-22.zip`

Keep it narrow. Include only:

```text
OWNER_RECHECK.md
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

Do **not** include all 30 runtime renditions or the entire promoted source tree in this owner ZIP.

`runtime-audit.json` must record:

- final commit SHA;
- focused/broader test commands and results;
- visual build/check results;
- six IDs / 30 variants inventory;
- failed-rendition cache implementation summary and bound;
- exact fault-injected assets and restoration proof;
- responsive rows actually exercised;
- cache/frame observations;
- evidence classification;
- explicit remaining unproven claims.

## 18. Stop conditions

Stop and report rather than improvising if:

- the fixture cannot be proven to run through the canonical Simulator source-loader path;
- simulator screenshots still do not correspond to the committed fixture surface and the discrepancy cannot be explained from architecture;
- fixing failure retry behavior would require a second asset loader/cache architecture;
- generated assets cannot be restored/validated after fault injection;
- a traceback/Linux shell is exposed to the child surface;
- the correction requires redesigning the accepted character art;
- the correction would deepen X11 coupling or bypass protected navigation architecture.

## 19. Git completion

Work on canonical `main`.

Before commit:

```bash
git status --short
make visual-assets
make visual-assets-check
# focused tests
# broader touched-module tests
git status --short
```

Then:

```bash
git add -A
git commit -m "fix(visual): bound character fallback failures and recheck simulator acceptance"
git pull --rebase origin main
git push origin main
git rev-parse HEAD
```

Do not force-push.

## 20. Final local-agent response

Return:

1. pushed commit SHA;
2. exact files changed;
3. focused/broader test results;
4. visual build/check results;
5. explanation of the bounded failed-rendition behavior and its bound;
6. simulator provenance result;
7. default-failure result;
8. responsive matrix actually run;
9. documentation synchronization result;
10. explicit remaining unproven claims;
11. exactly:

`VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_RUNTIME_RECHECK_2026-08-22.zip`

If any acceptance item fails, say so plainly and preserve the evidence. Do not report the gate as complete merely because source/tests/build steps passed.
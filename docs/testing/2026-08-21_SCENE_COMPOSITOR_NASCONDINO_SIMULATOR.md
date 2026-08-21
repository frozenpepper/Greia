# Greia Scene Compositor — Nascondino nel Bosco Simulator Gate

**Status:** owner/local-agent implementation + acceptance protocol  
**Date:** 2026-08-21  
**Evidence class when accepted:** `SIMULATOR VISUAL REVIEW`  
**Required runtime path:** Greia Activity Simulator, headless preferred  
**Graphics plan:** `docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md`  
**Mandatory visual evidence rules:** `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`

## 1. Goal

This is the first real use of Greia's scene/composition runtime.

Do **not** spend this tranche polishing launcher categories/buttons or building another proof-only Activity.

The target is the existing first-party Activity:

```text
activities/nascondino_bosco/
```

Its current gameplay remains intact, but its crude hand-drawn sky/pine/ground background must be replaced by the new shared Forest/Meadow scene runtime:

```text
assets/scenes/forest_meadow_day_v1.toml
src/greia_platform/scene.py
src/greia_platform/pygame_scene.py
```

The result should visibly demonstrate the graphics architecture:

```text
background/far scene layers
→ gameplay hiding spots and animals
→ foreground foliage + atmosphere/light
→ Activity UI
```

## 2. Hard rules

- Pull canonical `main` first.
- Work directly on `main`; do not create a branch.
- Do not use/query GitHub Actions.
- Do not expose Cloudflare/tunnels/hosted bridges.
- Use headless Activity Simulator for acceptance.
- Do not count direct `pytest`, `unittest`, `make test` or `make verify` as acceptance for this visual gate.
- `make visual-assets` is a build prerequisite only.
- Do not alter Nascondino's progression/storage/event IDs, hiding-map logic, launch lifecycle or protected Home behavior merely to fit the scene.
- Do not invent a parallel image cache or runtime asset loader.
- Do not rasterize SVG at Activity runtime.
- Do not silently keep the old primitive forest as the normal successful visual path. It is a **fallback only** after this tranche.
- Do not call the result visually accepted without the committed curated screenshots required below.

## 3. Preparation

```bash
git status --short
git branch --show-current
git pull --ff-only origin main

export GREIA_SIMULATOR_HEADLESS=1
export GREIA_SIMULATOR_STATE="$HOME/.greia-simulator-scene-compositor"
rm -rf "$GREIA_SIMULATOR_STATE"
rm -rf tmp/scene-compositor-nascondino-evidence
mkdir -p tmp/scene-compositor-nascondino-evidence

command -v rsvg-convert
make visual-assets
```

Confirm the generated catalogue includes the promoted Forest/Meadow IDs and confirm the following runtime directory exists:

```text
assets/visual/runtime/v1/forest_meadow/
```

At minimum confirm these generated PNGs exist:

```text
distant_hills.png
distant_treeline.png
cloud_large.png
cloud_small.png
tree_hero.png
tree_secondary.png
grass_edge.png
fog_strip.png
sunlight_rays.png
```

## 4. Integrate Nascondino with the scene runtime

Modify `activities/nascondino_bosco/main.py` cleanly rather than layering a hack over its frame loop.

### 4.1 Imports

Use the platform scene APIs:

```python
from greia_platform.pygame_scene import PygameSceneRenderer, SceneRenderError
from greia_platform.scene import SceneCamera, load_scene
```

### 4.2 Preserve the old background as an explicit fallback helper

Extract only the current primitive **background** drawing (sky/sun/pine backdrop/ground/rolling green ellipses) into a small helper such as:

```python
def _draw_legacy_forest_background(surface: pygame.Surface) -> None:
    ...
```

Do not move hiding spots, animals, particles, target card, progress UI or victory UI into that fallback helper.

### 4.3 Initialize the scene once

After Pygame/canvas initialization, create the scene and renderer once:

```python
root = Path(__file__).resolve().parents[2]
scene = load_scene(root / "assets" / "scenes" / "forest_meadow_day_v1.toml")
scene_renderer = PygameSceneRenderer.for_activity(max_entries=24)
scene_started = time.monotonic()
scene_failed = False
```

Do not rebuild the scene, catalogue or renderer every frame.

If scene initialization itself fails because required runtime scene data is unavailable, retain the legacy background for that Activity session. Do not crash the child into Linux/error output.

### 4.4 Background scene pass

At the start of the render portion, before hiding spots:

- compute `elapsed = time.monotonic() - scene_started`;
- use a very small deterministic camera drift or pointer-derived camera;
- render scene nodes through `max_z=59`;
- clear the canvas through the scene background on success;
- on `SceneRenderError`, mark `scene_failed = True` and use `_draw_legacy_forest_background(...)` for the rest of the session.

The camera movement must stay subtle. A good starting ceiling is roughly 8–12 design pixels horizontally and only a few vertically. Children must not feel that the world is sliding under them.

### 4.5 Gameplay pass

Draw existing hiding spots, clues, found-animal animation and particles exactly through the established Activity logic.

Do not relocate hit targets merely to fit decorative art.

### 4.6 Foreground/atmosphere pass

After gameplay world objects/particles, but **before the top target card / star pill / victory UI**, render the same scene again with:

```python
clear=False
min_z=60
```

This is the important composition proof: foreground foliage/fog/light may sit above the playfield while Activity UI remains above them.

All current z>=60 nodes are optional. A broken optional atmosphere/foreground asset should disappear narrowly rather than dropping the whole scene.

### 4.7 Static completeness

The same scene with `motion_enabled=False` must still look complete and intentionally composed. Motion is enrichment, not structural glue.

## 5. Start the simulator

```bash
python3 tools/greia_simulator.py --state-dir "$GREIA_SIMULATOR_STATE"
```

Use the loopback simulator bridge only:

```text
http://127.0.0.1:8767
```

Open `Nascondino nel Bosco` through the normal Collection-first child path. Do not launch the Python file directly as acceptance evidence.

## 6. Mandatory visual quality review — not optional

This gate is explicitly meant to stop the pattern where a local agent reports `PASS` while nobody later checks the pixels.

Follow `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`.

Reject and fix any of these before proceeding:

- clipped or truncated ordinary UI text;
- child-facing text materially below the Visual Style Guide's ~18 px lower guardrail at 1024×600;
- tiny/comically narrow buttons or labels;
- top UI colliding with scene artwork;
- hiding spots becoming visually lost against the background;
- foreground foliage covering interaction targets;
- stretched/distorted trees/clouds/panels;
- obvious rectangular alpha edges;
- fog/light making text harder to read;
- scene edges/crops looking accidental at 800-ish/1024 widths;
- large viewport composition becoming empty or oddly stretched;
- motion that is busy, seasick, or stronger than the gameplay.

A technically functional screenshot with those defects is **FAIL**, not PASS.

## 7. Baseline scene acceptance — 1024×600 normal

Capture a neutral frame shortly after entering the Activity.

Verify visually:

- shared hills/treeline/clouds establish depth;
- trees/bushes frame rather than wall off the playfield;
- gameplay hiding spots remain dominant and easy to click;
- authored Greia asset language is visibly richer than the old primitive background;
- target card and star pill stay cleanly above scene atmosphere;
- no clipped labels;
- no scene component looks like a stretched placeholder.

Raw evidence:

```text
tmp/scene-compositor-nascondino-evidence/01-reference-1024x600.png
```

## 8. Parallax / ambient-motion proof

Capture another frame several seconds later or after moving the synthetic pointer/camera enough to make the displacement visible.

Verify:

- clouds/far/mid/foreground layers have subtly different displacement;
- foliage sway is tiny;
- fog drift/light breathing is visible only on comparison, not distracting in isolation;
- gameplay hit geometry has not moved with decorative parallax.

Capture:

```text
tmp/scene-compositor-nascondino-evidence/02-motion-displaced.png
```

## 9. Static-motion-off proof

Temporarily exercise the renderer with ambient motion disabled while keeping the same scene.

Verify the frame still looks finished, grounded and readable.

Capture:

```text
tmp/scene-compositor-nascondino-evidence/03-static-motion-off.png
```

Restore normal motion afterward.

## 10. Required-scene fallback

Temporarily corrupt or move **one required** generated scene PNG, for example:

```text
assets/visual/runtime/v1/forest_meadow/distant_hills.png
```

Restart the isolated simulator and enter Nascondino normally.

Verify:

- Activity remains playable;
- it uses the explicit legacy forest background for that session;
- no repeated decode/error loop;
- no Linux error is exposed to the child;
- Activity UI/progression/inputs remain intact.

Capture raw evidence:

```text
tmp/scene-compositor-nascondino-evidence/10-required-fallback.png
```

Then restore generated assets with:

```bash
make visual-assets
```

## 11. Optional atmosphere isolation

Temporarily corrupt only:

```text
assets/visual/runtime/v1/forest_meadow/fog_strip.png
```

Verify the main shared forest scene still renders and remains playable; only the fog layer should disappear/fail softly.

Capture:

```text
tmp/scene-compositor-nascondino-evidence/11-optional-fog-fallback.png
```

Restore with `make visual-assets`.

## 12. Responsive matrix

Exercise the Activity through the simulator at:

| Row | Viewport | Interface size |
|---|---:|---|
| 1 | 1024×600 | normal |
| 2 | 1024×600 | large |
| 3 | 1280×800 | normal |
| 4 | 1366×768 | compact |
| 5 | 1920×1080 | normal |
| 6 | 1111×700 | normal |

Verify actual pixels at every row, especially:

- reference-canvas cover crop remains intentional;
- critical gameplay is not cropped;
- top UI remains readable;
- child-facing labels are not tiny/clipped;
- shared scene does not stretch non-uniformly;
- foreground framing remains at the edges;
- no resolution-specific production forks were added.

Store raw screenshots under:

```text
tmp/scene-compositor-nascondino-evidence/20-...
```

## 13. Frame/cache sanity

Measure 10 seconds after the scene cache is warm.

Record before/after simulator status. The aim is to detect starvation/regression against Greia's ~30 FPS clock, not make a physical Acer/Pi performance claim.

Also inspect/log the scene visual-cache entry count. It must stay bounded and should settle after the initial scene sizes are realized rather than continuously growing while idle.

## 14. Curated screenshots MUST be committed

Create:

```text
docs/reviews/visual/2026-08-21_scene-compositor-nascondino/
```

Commit **4–6 images only**, selected from the raw evidence, with these required semantic roles:

```text
01-reference.png          # 1024x600 normal neutral frame
02-motion.png             # visibly displaced ambient/parallax state
03-constrained.png        # 1024x600 large or other most stressful layout
04-large.png              # large viewport balance
05-fallback.png           # required scene fallback (optional fifth image)
```

Also commit:

```text
REVIEW.md
layout-audit.json
```

`REVIEW.md` must explicitly state whether text clipping, tiny text/buttons, overlap, distortion, poor margins, weak hierarchy or artwork obstruction were found. If found, fix them and replace the screenshots before calling the gate accepted.

This curated committed set exists specifically so the next reviewer can actually inspect the screenshots rather than trusting the local agent's prose.

## 15. Result/documentation updates

When accepted, update:

```text
LOCAL_AGENT_RESULT.md
docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
HANDOVER.md
```

Do not claim:

- physical Acer/Pi scene performance;
- Web scene renderer support;
- generic character-engine completion;
- all environment packs runtime-consumed;
- R7 closure.

## 16. Git completion

```bash
git status --short
git add -A
git commit -m "accept first Greia scene compositor in Nascondino simulator"
git pull --rebase origin main
git push origin main
git rev-parse HEAD
```

Do not force-push.

Return the final SHA plus concise acceptance matrix and the committed curated screenshot directory.

# Greia Scene Composition Runtime — Graphics Engine Tranche

**Status:** ACTIVE  
**Date:** 2026-08-21  
**Repository:** `frozenpepper/Greia` / `main`  
**Parent visual plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Stable architecture guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Visual evidence contract:** `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`

## Purpose

The V5 work proved that Greia can take reviewed semantic artwork through build-time PNG rendition, an explicit catalogue, bounded caches and real Shell consumers.

That plumbing is now sufficiently proven. The graphics workstream must stop spending its center of gravity on one more Shell button/category edge case and move to the missing runtime layer implied by the original visual architecture:

> **layered scene composition + parallax + ambient motion + reusable atmosphere/light/shadow + Activity-facing rendering**

This is intentionally **not** a general-purpose game engine or retained desktop compositor. It is a small Greia-specific graphics runtime for storybook/toy-diorama scenes on low-resource hardware.

## Architecture target

```text
reviewed semantic assets
        ↓
build-time PNG renditions
        ↓
AssetCatalogue
        ↓
PygameVisualSurfaceCache
        ↓
renderer-neutral SceneDefinition
        ↓
PygameSceneRenderer
        ↓
Activity scene
  ├─ background/far layers
  ├─ mid/playfield layers
  ├─ gameplay/characters
  ├─ foreground framing
  └─ atmosphere/light/FX
```

Future Web Activities must preserve the same scene semantics through a Web renderer/transport rather than copying Pygame internals.

## Hard constraints

- no runtime SVG rasterization;
- no arbitrary directory scanning;
- no unbounded caches;
- no per-frame image decode/scale after cache warm-up;
- no heavyweight 3D/scene-graph dependency;
- no scene object may gain Activity lifecycle/security/input authority;
- a complete static frame must remain coherent with ambient motion disabled;
- motion primitives must be cheap and bounded;
- composition must work from a reference authoring canvas across Greia viewports;
- critical gameplay stays inside declared safe composition space;
- visual acceptance requires actual screenshot review under `VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`.

## S1 — Core scene model and Pygame compositor **[ACCEPTED: SIMULATOR VISUAL REVIEW]**

Current source:

```text
src/greia_platform/scene.py
src/greia_platform/pygame_scene.py
tests/test_scene.py
```

Implemented concepts:

- fixed authoring canvas;
- `cover` / `contain` viewport mapping;
- explicit semantic visual nodes;
- stable z ordering;
- per-node alpha;
- bounded 0..1 parallax factor;
- deterministic ambient primitives:
  - `drift_x`;
  - `drift_y`;
  - `float`;
  - `sway_x`;
  - `breathe_alpha`;
- optional-node fail-soft isolation;
- required-node scene failure so an Activity can retain a deliberate static/private fallback;
- split z-range rendering so gameplay may sit between background and foreground/atmosphere passes;
- shared `PygameVisualSurfaceCache`, not a second image-cache framework.

Unit tests: 10/10 passed (`tests/test_scene.py`).

## S2 — First real runtime scene: Forest/Meadow **[ACCEPTED: SIMULATOR VISUAL REVIEW]**

First runtime scene manifest:

```text
assets/scenes/forest_meadow_day_v1.toml
```

The runtime rendition source manifest now promotes a bounded first environment set using the **same semantic IDs already present in the Forest/Meadow source catalogue**, including:

```text
hills.distant.01
treeline.distant.01
cloud.large.01
cloud.small.01
tree.hero.01
tree.secondary.01
bush.round.01
bush.flowering.01
bush.low.01
fern.cluster.01
log.fallen.01
rock.cluster.large.01
ground.grass_edge.01
atmosphere.fog_strip.01
atmosphere.sunlight_rays.01
```

The authored reference scene uses 1024×600 design coordinates and keeps critical gameplay inside the central 800 px safe span so `cover` cropping remains safe on 4:3 displays.

## S3 — First Activity acceptance (Nascondino nel Bosco) **[ACCEPTED: SIMULATOR VISUAL REVIEW]**

Acceptance protocol:

```text
docs/testing/2026-08-21_SCENE_COMPOSITOR_NASCONDINO_SIMULATOR.md
```

Accepted outcome:

- Nascondino uses the shared Forest/Meadow scene for its world/background;
- gameplay spots/animals remain interaction-authoritative;
- background scene renders before gameplay ($z \le 59$);
- foreground foliage + atmosphere/light render after gameplay ($z \ge 60$) but before Activity UI;
- subtle parallax/ambient life is visible and calm;
- motion-off frame is complete;
- missing/corrupt required scene art (`distant_hills.png`) triggers the Activity's deliberate legacy forest fallback;
- optional atmosphere failure (`fog_strip.png`) skips only the affected layer;
- all six responsive matrix rows passed;
- FPS/cache behavior remained bounded (~27.5 FPS simulator sanity);
- curated screenshot set committed under `docs/reviews/visual/2026-08-21_scene-compositor-nascondino/` with `REVIEW.md` and `layout-audit.json`.

## S4 — Motion/scene vocabulary expansion **[NEXT]**

Only after S3 is visually accepted, add primitives justified by real callers. Candidate needs:

- quantized tiny tilt/rotation if foliage still needs it;
- bounded sprite/face-state swapping for Puff/Bean characters;
- repeating/tiled water or shimmer where Water/Pond proves the need;
- simple color/light pulse;
- scene-local character placement and shared shadow grounding;
- optional low-count particle emitters only if static SVG FX are insufficient.

Do not create generic nodes/components speculatively.

## S5 — Character and reusable FX integration

Use Lilli/Nino/Tito/Momo as scene entities without returning to detailed skeletal rigs.

Target behavior:

- semantic character art/state;
- whole-character translation/bob/squash/stretch;
- authored face-state swaps;
- shared contact shadow;
- same scene z/parallax model;
- deterministic idle timing;
- complete static state.

## S6 — Activity authoring adapter

Python Activities should be able to declare/use a scene without recreating cache/loading/parallax machinery.

The adapter should expose composition semantics, not host paths or Pygame internals where avoidable.

The existing `get_shared_visual(...)` API remains valid for isolated assets. The scene API is an additional higher-level composition service, not a replacement.

## S7 — Web renderer/transport

After the Python/Pygame scene contract proves stable:

```text
SceneDefinition semantics
→ Greia-controlled Web asset handles/URLs
→ bounded HTML/Canvas renderer
```

Do not expose host filesystem paths to Web content and do not invent a second semantic scene vocabulary.

## S8 — Low-resource / physical proof

Simulator FPS is regression evidence, not Acer/Pi performance proof.

A later physical gate should measure:

- startup/decode/cache warm-up;
- steady scene frame rate;
- memory footprint;
- resize/re-entry behavior;
- static-motion-disabled fallback;
- cache ceilings;
- absence of runtime SVG dependencies.

R7 remains independently open; this graphics tranche does not close display/session/input architecture.

## Evidence discipline

Visual acceptance now requires committed reviewable screenshots. Local temporary screenshot names in a result report are insufficient because later reviewers cannot inspect their pixels.

Follow:

```text
docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
```

Keep only 4–6 curated PNGs per substantive gate in Git; full raw matrix evidence remains project-local.

# Greia Scene Composition Runtime

**Status:** active architecture; first source implementation landed, simulator acceptance pending  
**Date:** 2026-08-21  
**Parent visual architecture:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Implementation plan:** `docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md`

## Purpose

Greia needs richer Activities and system scenes without requiring every Activity to hand-code backgrounds, parallax, fog, light, cache logic and responsive placement.

The scene runtime provides a small renderer-neutral composition model specifically for Greia's storybook/toy-diorama visual language and low-resource hardware.

It is **not**:

- a generic retained scene graph;
- a replacement for Pygame;
- a 3D engine;
- a physics engine;
- an Activity lifecycle/input/security owner;
- a filesystem asset browser.

## Core model

A scene is authored against a fixed reference canvas, normally `1024×600`.

A `SceneDefinition` contains ordered semantic visual nodes. Each node contains only bounded presentation facts:

```text
node id
semantic asset id
explicit variant
reference-canvas rectangle
z depth
alpha
parallax factor
optional ambient motion
required/optional visual status
```

The renderer maps the reference canvas to the real viewport using one uniform scale.

Current fit policies:

- `cover` — fill the viewport, crop symmetric outer edges where aspect ratios differ;
- `contain` — keep the full authored canvas visible and accept letterboxed spare space.

For Greia world scenes, `cover` is normally preferred while interactive/critical content stays inside the declared central safe composition span.

## Layering contract

Typical runtime composition:

```text
0–29   sky / far background
30–39  mid background / framing
40–59  playfield support / non-interactive props

        Activity gameplay/interactive objects

60–79  foreground framing
80–89  atmosphere
90–99  light / visual FX

        Activity UI / protected Greia chrome
```

Exact z values are scene-owned. The stable requirement is that the renderer can draw bounded z ranges so gameplay can sit between background and foreground/atmosphere passes.

## Semantic assets only

Scene nodes reference IDs such as:

```text
hills.distant.01
tree.hero.01
ground.grass_edge.01
atmosphere.fog_strip.01
```

They do not reference arbitrary host file paths.

Runtime resolution remains:

```text
SceneDefinition
→ semantic asset ID / variant
→ AssetCatalogue
→ PygameVisualSurfaceCache
→ generated PNG surface
```

Source SVGs remain authoring/build inputs. Target Activities do not rasterize them.

## Parallax

Each node may declare a bounded `0..1` parallax factor.

The caller supplies a camera offset in reference-canvas pixels. Nodes subtract a fraction of that offset according to depth.

The camera is presentation only. It must not alter gameplay hit geometry unless an Activity explicitly chooses to bind gameplay to the same world coordinates.

For ordinary Greia storybook scenes camera motion should remain small—normally a few design pixels, not platformer-style world scrolling.

## Ambient motion

Current cheap deterministic primitives:

```text
none
drift_x
drift_y
float
sway_x
breathe_alpha
```

The primitives intentionally use simple periodic sampling. They create no timeline objects, require no network/disk access, and remain coherent when disabled.

Current `sway_x` is a tiny translation, not per-frame arbitrary rotation. If real callers later prove that quantized tilt is visually necessary, add it as a bounded shared primitive rather than introducing per-Activity rotation loops.

## Static completeness

`motion_enabled=False` is a first-class mode.

A valid Greia scene must still look intentionally composed when ambient motion is disabled because:

- low-resource fallback may reduce animation;
- accessibility/preferences may later reduce motion;
- screenshots/thumbnails need stable frames;
- motion must never carry essential meaning.

## Failure behavior

A scene node is either required or optional.

- **required node failure:** the Pygame renderer raises a scene-level render error so the Activity can switch to a deliberate static/private fallback;
- **optional node failure:** only that decorative layer is skipped.

This is deliberately narrower than swallowing errors around the entire Activity frame loop.

## Current source owners

```text
src/greia_platform/scene.py
src/greia_platform/pygame_scene.py
assets/scenes/forest_meadow_day_v1.toml
assets/catalog/shared_visuals_v1_source.toml
tests/test_scene.py
```

First integration target:

```text
activities/nascondino_bosco/
```

Acceptance:

```text
2026-08-21_SCENE_COMPOSITOR_NASCONDINO_SIMULATOR.md (archived; see git history)
```

## Pygame realization

`PygameSceneRenderer` uses the existing `PygameVisualSurfaceCache`.

It does not create another cache framework.

The first scene renderer factory uses a larger but still hard-bounded cache (`24` entries by default) because a real layered scene legitimately references more simultaneous surfaces than a small Shell component.

Important runtime rules remain:

- cache final semantic ID + variant + requested size;
- no repeated PNG decode after cache hit;
- no runtime SVG;
- clear cache explicitly when a caller's meaningful target-size policy changes;
- do not grow cache entries indefinitely with continuously varying sizes.

The first reference Activity uses the established fixed `1024×600` Activity canvas, which keeps scene rendition sizes stable while the platform canvas handles physical viewport presentation.

## Responsive composition

The scene model is intentionally separate from Activity hit-layout logic.

The first reference scene uses `1024×600` design coordinates and keeps critical gameplay inside a central safe span. On a 4:3 display, `cover` may crop decorative outer framing while keeping gameplay intact. On wider displays, symmetric top/bottom or side cropping/extension remains predictable.

Do not solve responsive scene problems with per-device coordinate tables.

## Future renderer parity

Python/Pygame is the first renderer, not the semantic definition of scenes.

Future Web Activities should consume the same concepts:

```text
SceneDefinition semantics
→ Greia-authorized Web asset handles/URLs
→ Canvas/DOM renderer
```

Do not expose host paths to Web content and do not create a second scene vocabulary.

## Visual acceptance

Scene work requires actual pixel review.

Follow:

```text
docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
```

A simulator run that only records state JSON/FPS is not sufficient to call a scene visually accepted. The local agent must commit a small curated screenshot set so subsequent reviewers can inspect text size, clipping, hierarchy, composition, crop quality, artwork distortion and interaction obstruction.

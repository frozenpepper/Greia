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
- visual acceptance requires actual screenshot review under `VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`;
- numeric visual evidence must agree with source/runtime values rather than being hand-transcribed.

## S1 — Core scene model and Pygame compositor **[RUNTIME PROVEN IN SIMULATOR; PRIMARY PIXEL REVIEW NOT INDEPENDENTLY CLOSED]**

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
- optional decode/load failures remembered per renderer realization so a corrupt decorative asset is not retried every frame;
- required-node scene failure so an Activity can retain a deliberate static/private fallback;
- split z-range rendering so gameplay may sit between background and foreground/atmosphere passes;
- shared `PygameVisualSurfaceCache`, not a second image-cache framework.

Source unit coverage exists in `tests/test_scene.py`. For the owner-directed visual workstream, Activity Simulator evidence remains the acceptance path; committed source tests are not promoted to current PASS merely by existing.

## S2 — First real runtime scene: Forest/Meadow **[RUNTIME PROVEN IN SIMULATOR]**

First runtime scene manifest:

```text
assets/scenes/forest_meadow_day_v1.toml
```

The runtime rendition source manifest promotes a bounded first environment set using the **same semantic IDs already present in the Forest/Meadow source catalogue**, including:

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

The authored reference scene uses 1024×600 design coordinates, `fit = "cover"`, and keeps critical gameplay inside the central safe span so centered edge crop remains safe on differing aspect ratios.

## S3 — First Activity integration: Nascondino nel Bosco **[SIMULATOR RUNTIME EVIDENCE RETAINED; EVIDENCE AUDIT CORRECTION OPEN]**

Protocol executed:

```text
2026-08-21_SCENE_COMPOSITOR_NASCONDINO_SIMULATOR.md (archived; see git history)
```

Retained runtime facts:

- Nascondino uses the shared Forest/Meadow scene for its world/background;
- gameplay spots/animals remain interaction-authoritative;
- background scene renders before gameplay (`z <= 59`);
- foreground foliage + atmosphere/light render after gameplay (`z >= 60`) but before Activity UI;
- subtle parallax/ambient life is active;
- motion-off frame exists;
- missing/corrupt required scene art (`distant_hills.png`) triggers the Activity's deliberate legacy forest fallback;
- optional atmosphere failure (`fog_strip.png`) skips only the affected layer;
- the six responsive simulator rows were exercised;
- measured scene run was **258 frames / 10.01 s = 25.8 FPS** simulator sanity;
- curated screenshots are committed under `docs/reviews/visual/2026-08-21_scene-compositor-nascondino/` (archived; see git history).

Primary source/evidence cross-check:

```text
docs/reviews/visual/2026-08-21_scene-compositor-nascondino/PRIMARY_REVIEW.md (archived; see git history)
```

That review found the local-agent visual audit overstated/incorrectly transcribed several facts: target label was 18 px rather than claimed 22 px; recorded target-card geometry disagreed with source; Large-interface scaling was claimed where the fixed HUD did not use that preference; and the scene's `cover` behavior was described as letterbox/pillarbox. These are folded into the next actor/HUD gate instead of starting another isolated micro-cycle.

## S4 — Shared scene actor / first character-state runtime **[SIMULATOR ACCEPTED; EVIDENCE ZIP PREPARED FOR OWNER REVIEW]**

New renderer-neutral source:

```text
src/greia_platform/scene_actor.py
```

Implemented actor semantics:

- semantic character asset ID + explicit state variant;
- deterministic blink state swap;
- cheap whole-character vertical idle motion;
- independently grounded shared contact shadow;
- scene z/parallax placement;
- complete `motion_enabled=False` static sample;
- output remains ordinary `SceneNode` data and therefore reuses `PygameSceneRenderer` / existing cache;
- no skeletal rig, per-frame raster generation, or second character renderer/cache.

Promoted runtime actor assets:

```text
character.lilli/default
character.lilli/blink
shadow.contact.small.01/default
```

Build-time outputs:

```text
assets/visual/runtime/v1/characters/lilli_neutral.png
assets/visual/runtime/v1/characters/lilli_blink.png
assets/visual/runtime/v1/shared/shadow_contact_small.png
```

Simulator runbook executed:

```text
docs/testing/2026-08-21_SCENE_ACTOR_LILLI_NASCONDINO_SIMULATOR.md
```

Accepted simulator facts:
- Scene Actor Lilli guide + grounded contact shadow rendered via existing `PygameSceneRenderer` and bounded surface cache;
- deterministic blink (eyes closed smiling curve) and subtle vertical idle motion ($\pm 3$ px) verified;
- Nascondino target HUD corrected with **24 px** animal font in Normal, **26 px** in Large, **20 px** in Compact;
- `SCOIATTOLO` fits cleanly inside available text spans across all interface sizes without clipping, collision, or ellipsis;
- 112 px clear horizontal safety margin between star pill ($x=210$) and target card ($x=322..337$);
- 10-second idle performance sanity: 230 frames / 10.01 s = **23.0 FPS**;
- Curated screenshot review set committed under `docs/reviews/visual/2026-08-21_scene-actor-lilli-nascondino/` (archived; see git history);
- Transfer archive prepared at project root for independent owner/ChatGPT pixel inspection: `./GREIA_VISUAL_REVIEW_SCENE_ACTOR_LILLI_2026-08-21.zip`.

## S5 — Character and reusable FX integration

After the first Lilli actor gate, extend only from real caller needs.

Target behavior:

- semantic character art/state;
- whole-character translation/bob/squash/stretch where bounded cache behavior remains stable;
- authored face-state swaps;
- shared contact shadow;
- same scene z/parallax model;
- deterministic idle timing;
- complete static state.

Candidate additions must be justified by real Activities. Quantized tiny tilt, simple light/color pulse, Water/Pond shimmer or low-count particle emitters are not automatically next merely because they are possible.

## S6 — Activity authoring adapter

Python Activities should be able to declare/use a scene and scene actors without recreating cache/loading/parallax machinery.

The adapter should expose composition semantics, not host paths or Pygame internals where avoidable.

The existing `get_shared_visual(...)` API remains valid for isolated assets. The scene API is an additional higher-level composition service, not a replacement.

## S7 — Web renderer/transport

After the Python/Pygame scene + actor contract proves stable:

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
- aggregate cache ceilings;
- absence of runtime SVG dependencies.

R7 remains independently open; this graphics tranche does not close display/session/input architecture.

## Evidence discipline

Visual acceptance requires committed reviewable screenshots, but local-agent prose is not assumed correct merely because screenshots exist. The primary/source cross-check must reject numeric or fit-mode claims that disagree with runtime source.

Follow:

```text
docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
```

Keep only 4–6 curated PNGs per substantive gate in Git; full raw matrix evidence remains project-local.

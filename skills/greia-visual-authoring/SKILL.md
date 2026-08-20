---
name: greia-visual-authoring
description: Practical guide for producing and integrating reusable Greia visual assets, characters, backgrounds, props, FX and UI in the constraint-native Greia style.
---

# Greia Visual Authoring Skill

**Status:** living derived guide  
**Reviewed:** 2026-08-20  
**Main visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Active art plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Current resume:** `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`

Before substantial visual work, read the main visual-system guide. This skill is the practical production checklist; it does not duplicate the full architecture/index.

## 1. Core production rule

Greia visual work is **asset-first**.

Do not begin by drawing a crude full screen and then calling it a style direction. Build strong reusable pieces first, review those pieces individually, then compose scenes and UI from them.

The production model is:

> **excellent individual assets → coherent packs → layered composition → subtle animation/parallax/light/shadow → explicit semantic runtime consumption → Shell/Activity reuse**

HTML/mock screens are review tools only. They are not a substitute for good art.

## 2. Quality bar

The simplified Greia character language is a constraint solution, not permission to make cheap primitive art.

Reusable assets should aim for:

- polished storybook / toy-diorama quality;
- strong silhouette;
- controlled texture and internal detail;
- soft depth and readable form;
- coherent warm lighting;
- useful local highlights and cast/contact shadows;
- clean transparent edges for composable assets;
- readability at the intended size;
- compatibility with other Greia assets without looking copy-pasted.

Reject final represented art that looks like tutorial circles/rectangles/polygons unless the object is intentionally geometric.

## 3. Characters

Working shared cast:

- Lilli — unicorn Puff;
- Nino — owl Bean;
- Tito — fox Puff;
- Momo — friendly monster Puff.

Default character grammar:

- one dominant body mass;
- large readable face;
- tiny/optional appendages;
- identity through silhouette, ears/horn/tuft/tail/marking/accessory;
- whole-body motion rather than complex anatomical rigs.

Shared base motions:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Hard rules:

- preserve the same character art across states;
- `blink` must physically read as closed eyes;
- do not add fake overlays that degrade the face;
- character work must not monopolize the visual workstream when current integration work has priority.

## 4. Environment assets

Build scenes from reusable assets.

Preferred environment asset types:

- hero trees / secondary trees;
- bushes / foliage clumps;
- flowers / mushrooms;
- rocks / logs;
- grass / ground edges;
- clouds;
- distant hills / mountains / tree lines;
- houses / castles / village pieces;
- furniture / workshop / clinic props;
- foreground framing elements;
- atmosphere/light overlays;
- shadow assets;
- ambient FX.

### Layering model

Typical scene order:

1. sky/room base;
2. far background;
3. mid background;
4. ground/playfield;
5. props/interactive assets;
6. foreground framing;
7. atmosphere/light;
8. characters/UI.

Keep interactive objects visually separable from decoration.

## 5. Parallax and ambient animation

Prefer subtle cheap motion:

- slow cloud drift;
- far/mid/foreground parallax ratios;
- small foliage sway;
- firefly fade/move;
- dust/fog drift;
- water shimmer;
- gentle light-ray breathing;
- tiny prop idle movement.

Do not animate everything. Motion should create life and depth, not noise.

## 6. Light and shadow

Lighting is a shared visual system.

Create/reuse assets/treatments for:

- contact shadows;
- cast-shadow decals;
- warm/cool glows;
- sun/window/moonlight shafts;
- haze/fog;
- foreground vignette shadows;
- reward/discovery light effects.

A composable asset should normally have a clear plan for grounding and lighting in a scene.

## 7. UI visual assets

Build/reuse families for:

- primary/secondary/quiet buttons;
- icon buttons;
- cards;
- panels/sheets;
- tabs/category pills;
- avatar/profile frames;
- progress bars/pills;
- status badges;
- speech/thought/help bubbles;
- reward/help/error/loading/empty-state pieces;
- selection/focus/hover/pressed visuals;
- common shadows/highlights/trims.

UI must remain large and readable at 800×600 and 1024×600.

UI motion vocabulary:

- hover/focus → tiny lift + shadow/highlight;
- press → small squash/depress;
- launch → short bounce/squiggle/pop;
- selected → stronger frame/depth/glow;
- reward → sparkle + pop;
- gentle error → restrained wobble.

Protected Greia Home/Back chrome remains platform-owned and must not be imitated or replaced by Activity artwork.

## 8. Asset review workflow

For each pack:

1. prove a real reuse/coverage gap exists;
2. inspect existing shared assets first;
3. list the individual assets;
4. produce/revise the individual high-quality assets;
5. review each asset on representative grounds and at intended size;
6. reject or fix weak assets before scene assembly;
7. record provenance/status;
8. compose a small reference scene using only accepted pieces;
9. add parallax/subtle motion where appropriate;
10. integrate only after the underlying assets are worth reusing.

Never hide weak assets inside a busy composition.

## 9. Current active phase — V5 integration

Broad environment/UI source coverage now exists through Forest/Meadow, Shared UI, Workshop, Clinic/Care, Reading/Classroom, Fantasy/Village/Night and Water/Pond.

**Do not create another environment family by default.** A new pack requires a concrete reusable coverage gap.

The active work is V5 shared consumption/integration. The current first Shell consumer is:

```text
ui.shadow.soft
```

The integration architecture is:

```text
reviewed SVG master
→ explicit source manifest
→ build-time PNG rendition
→ explicit generated runtime catalogue
→ AssetCatalogue
→ PygameVisualSurfaceCache
→ real Shell consumer
```

Hard integration rules:

- do not scan `assets/visual/` at runtime;
- do not rasterize SVG on the target;
- do not create a second catalogue or image cache;
- do not decode/scale PNGs every frame;
- keep caches bounded;
- keep the existing primitive/static visual path as fallback for optional shared artwork during initial integration;
- do not change launcher geometry merely to prove asset consumption;
- do not add simulator-specific production code.

Current local-agent protocol:

`docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md`

For that current owner-directed tranche, runtime/visual/fallback/responsive acceptance is performed through the Activity Simulator.

## 10. Evidence and progress

Use accurate labels:

- DESIGN SPEC;
- SOURCE;
- DESKTOP VISUAL REVIEW;
- SIMULATOR VISUAL REVIEW;
- PHYSICAL VISUAL REVIEW;
- REJECTED EXPERIMENT.

After substantive visual work:

- update the checkpoint/progress log in `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`;
- update `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` if the continuation state changed;
- update `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` if the stable visual architecture/index changed;
- update `HANDOVER.md` when the project-wide continuation/evidence boundary changed.

## 11. Explicit failure patterns

Do not repeat without new evidence:

- one-shot AI sprite sheets assumed production-ready;
- complex automatic quadruped rigs as the default solution;
- vector recreations that visibly lose the source character identity;
- fake face overlays that make characters worse;
- non-blinking `blink` animations;
- primitive mock backgrounds presented as production art;
- scene-first HTML demos before reusable assets exist;
- random unrelated art direction per Activity;
- spending the entire visual effort on mascot mechanics while UI, props, lighting and backgrounds remain untouched;
- adding new environment packs merely to avoid integration work;
- runtime SVG rendering;
- arbitrary visual-directory scanning;
- parallel per-Activity/shared-visual frameworks;
- unbounded or per-frame image decoding caches.
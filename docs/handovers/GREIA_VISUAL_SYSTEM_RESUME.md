# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Visual-authoring architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic art taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`  
**Maintainer visual-toolbox plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`

---

# 1. Critical correction

Do not resume the old themed-pack sequence as though each historical scene family were automatically a core generic pack.

The current architecture has two tracks:

## Track A — maintainer-side generic visual toolbox

The owner's local agent is used to create/improve Greia source art. Its abilities are not evidence about arbitrary future user agents.

Useful reviewed source bundles currently include:

- Forest/Meadow v0.3 — promoted;
- Workshop v0.2 — promoted;
- Clinic/Care 2026-08-21 candidate — visually stronger than its baseline in many roles, but **not authorized as a core Clinic pack**.

Themed bundles are source/provenance pools. The primary Activity-authoring interface should be generic semantic collections.

Current generic taxonomy:

```text
Nature & Landscape
Interiors & Architecture
Furniture & Storage
Everyday Props & Containers
Making, Learning & Play
Lighting, Atmosphere, FX & Shadows
Shared UI
Canonical Characters
```

Authority:

```text
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
```

## Track B — arbitrary Activity-authoring agents

The user-facing skill is model/tool agnostic and teaches:

```text
inventory Activity needs
→ search generic semantic authoring library
→ inspect source/reference art as needed
→ REUSE, COMPOSE/ADAPT, or CREATE ORIGINAL
→ create Activity-local final art where needed
→ flatten/build efficient runtime rendition
→ integrate through existing Greia package/scene boundaries
→ inspect actual pixels
```

Authority:

```text
skills/greia-visual-authoring/SKILL.md
```

---

# 2. Current exact maintainer task

Do **not** execute Clinic/Care promotion/finalization as the next core-pack action.

Execute:

```text
docs/testing/2026-08-21_GENERIC_VISUAL_LIBRARY_CONSOLIDATION.md
```

That task must:

1. create `assets/visual/authoring_library/` generic indexes;
2. map promoted Forest/Meadow v0.3 into generic collections;
3. map promoted Workshop v0.2 into generic collections;
4. classify Clinic candidate assets as `GENERIC_INDEX`, `SPECIALIZED_THEME_ONLY`, or `UNRESOLVED`;
5. reference assets by source path instead of duplicating files;
6. produce a generic coverage-gap report;
7. recommend the next **generic** art-production batch by cross-Activity usefulness.

Do not blindly continue to Reading/Classroom, Fantasy/Village/Night or Water/Pond as core packs.

---

# 3. Current source-art state

## Forest / Meadow v0.3

Promoted source bundle:

```text
28 semantic roles
= 23 reauthored roles
+ 5 retained legacy roles
+ 2 preferred ingredients
```

Best understood as a source pool feeding generic Nature/Landscape and lighting/FX collections.

## Workshop v0.2

Promoted source bundle:

```text
24 finished semantic assets
= 14 direct reauthored replacements
+ 5 retained baseline variants
+ 5 candidate coexistence variants
+ 2 preferred ingredients
```

Best understood as a source pool feeding generic Interiors, Furniture/Storage, Making/Learning/Play, Everyday Props and Lighting collections.

## Clinic / Care candidate

The candidate contains strong reusable art, but its theme is too specialized to justify automatic core-pack promotion.

Likely generic harvest candidates include room/furniture/comfort assets such as bed, cabinet, table, cushion, rug, curtains, window, wall/floor bases, plush toy and neutral containers where appropriate.

Strongly medical props such as stethoscope, bandage-specific container and care kit should remain specialized unless repeated real Activity demand justifies a domain extension.

Do not create `clinic/v0.2` during generic consolidation.

---

# 4. Stable runtime foundation

Preserve the existing runtime architecture:

```text
explicit semantic asset catalogues
build-time SVG/source → runtime PNG renditions
bounded Pygame visual cache
SceneDefinition / SceneNode / SceneCamera
PygameSceneRenderer
SceneActorDefinition / actor_scene_sample
```

Runtime rules remain:

- no arbitrary runtime source-directory scanning;
- no ordinary target SVG rasterization;
- no per-frame disk decode/scale;
- bounded caches;
- explicit semantic/shared assets;
- Activity-local assets remain inside the Activity package;
- extend existing package/scene seams rather than inventing parallel loaders.

The generic authoring indexes are an **authoring/discovery layer**, not a second runtime asset system.

---

# 5. Permanent authoring principles

- Rich composition at authoring time; economical composition at runtime.
- Reuse does not mean clone-everywhere reuse.
- The generic library is a toolbox, not a promise to contain every final object.
- Specialized Activity art is expected and should usually remain Activity-local.
- A visually good source asset may still be too specialized for the generic core.
- Newer does not automatically replace older.
- Useful old/new variants may coexist under distinct semantic IDs.
- The producing agent's prose is not visual evidence; inspect actual pixels.

---

# 6. Nascondino lesson

Nascondino proved scene-runtime plumbing but exposed the failure mode where a polished background sits behind primitive gameplay art.

The correct future Activity workflow is:

```text
search generic toolbox
→ reuse/adapt/create Activity-local art for ALL important visible gameplay roles
→ compose environment + interactive props + characters + feedback + UI coherently
```

Do not solve this by globally shipping every possible hiding tree, medical prop, machine or animal pose.

---

# 7. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content correction closes, reorders or bypasses R7.

No physical Acer/Pi acceptance should be claimed unless actually performed.

---

# 8. Do not resume these drift directions

- themed-pack-by-themed-pack reauthoring without asking whether the theme is broadly reusable;
- endless per-object optimization;
- treating the local agent as representative of user agents;
- building a giant shared warehouse of every possible final prop;
- background-only Activity polish;
- rigid geometric authoring templates;
- arbitrary runtime asset discovery;
- second catalogue/cache frameworks;
- Shell/category micro-polish as a substitute for the visual-authoring system.

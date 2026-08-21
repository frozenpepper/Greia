# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Visual-authoring architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic art taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`  
**Maintainer toolbox plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`

---

# 1. Current architectural direction

The visual workstream has two separate tracks.

## Track A — maintainer-side generic visual toolbox

The owner's local agent is used to create/improve Greia source art. Its capabilities are not evidence about arbitrary user agents.

Theme/environment bundles are source/provenance pools. The primary Activity-authoring discovery layer is the generic semantic library:

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

## Track B — arbitrary Activity-authoring agents

The model/tool-agnostic workflow remains:

```text
inventory Activity needs
→ search generic semantic authoring library
→ prefer reviewed/preferred resources where they genuinely fit
→ inspect candidate/source references as needed
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local final art
→ flatten/build efficient runtime rendition
→ integrate through existing Greia package/scene boundaries
→ inspect actual pixels
```

Authority:

`skills/greia-visual-authoring/SKILL.md`

---

# 2. Current source-art state

## Forest / Meadow v0.3

Promoted source pool:

```text
28 semantic roles
= 23 reauthored roles
+ 5 retained legacy roles
+ 2 preferred authoring ingredients
```

## Workshop v0.2

Promoted source pool:

```text
24 finished semantic assets
= 14 direct reauthored replacements
+ 5 retained baseline variants
+ 5 candidate coexistence variants
+ 2 preferred ingredients
```

## Clinic / Care 2026-08-21 candidate

Useful reviewed source pool. It is not a required core generic pack. Generic furniture/interior/comfort/neutral-container assets may be indexed; strongly medical assets remain specialized.

No `clinic/v0.2` core-pack promotion is authorized merely because the candidate exists.

---

# 3. First generic consolidation result

Commit `cc1d7f1` created:

`assets/visual/authoring_library/`

with six semantic collection indexes and harvested Forest/Meadow, Workshop and Clinic candidate resources.

The **structure is useful and retained**.

However, the resulting gap analysis is not authoritative because it omitted existing source pools:

- Reading / Classroom v0.1;
- Fantasy / Village / Night v0.1;
- Water / Pond v0.1.

This is a material omission. Reading already contains books, reading chair, beanbag, potted plant, toy basket, bookcase, floor cushion, etc. Water already contains pond/water/reeds/dock/stepping-stone and water FX resources. Fantasy already contains reusable bridge/signpost/well/lantern/cobblestone candidates.

Therefore the previously recommended 16-asset generic batch is **NOT AUTHORIZED YET**.

Primary review:

`docs/reviews/visual/2026-08-21_generic-authoring-library-consolidation/PRIMARY_REVIEW.md`

---

# 4. Exact current maintainer task

Execute:

`docs/testing/2026-08-21_GENERIC_VISUAL_LIBRARY_FULL_SOURCE_HARVEST.md`

This is an inventory/classification/review gate, not an art-production gate.

It must:

1. inspect all Reading/Classroom v0.1 assets;
2. inspect all Fantasy/Village/Night v0.1 assets;
3. inspect all Water/Pond v0.1 assets;
4. classify every relevant source as:
   - `PREFERRED_GENERIC`
   - `CANDIDATE_GENERIC`
   - `REAUTHOR_GENERIC`
   - `SPECIALIZED_THEME_ONLY`
   - `DUPLICATE_OR_SUPERSEDED`
   - `UNRESOLVED`
5. update generic indexes without duplicating source files;
6. distinguish `preferred` resources from `candidate_reference` resources;
7. generate owner-review screenshots for the newly harvested generic candidates;
8. recompute gaps as:
   - `TRUE_MISSING`
   - `QUALITY_GAP`
   - `VARIETY_GAP`
   - `NO_GAP`
9. only then recommend the next generic art-production batch.

No new art should be drawn during this gate.

---

# 5. Generic-library admission rule

The semantic index structure is canonical. Individual assets are not automatically equally canonical/preferred.

Generic entries should expose a simple admission state:

```text
preferred
candidate_reference
```

Use preferred assets first for direct REUSE. Candidate references may still support COMPOSE/ADAPT or inspiration.

An existing weak source asset means `QUALITY_GAP`, not `TRUE_MISSING`.

---

# 6. Stable runtime foundation

Preserve:

```text
explicit semantic asset catalogues
build-time SVG/source → runtime PNG renditions
bounded Pygame visual cache
SceneDefinition / SceneNode / SceneCamera
PygameSceneRenderer
SceneActorDefinition / actor_scene_sample
```

Runtime rules remain:

- no arbitrary runtime source scanning;
- no ordinary target SVG rasterization;
- no per-frame disk decode/scale;
- bounded caches;
- Activity-local assets remain inside Activity packages;
- generic authoring indexes are an authoring/discovery layer, not a second runtime catalogue.

---

# 7. Nascondino lesson

Nascondino showed the failure mode where the background is upgraded while gameplay art remains primitive.

The intended Activity workflow remains:

```text
search generic toolbox
→ reuse/adapt/create all important visible gameplay art coherently
→ integrate environment + interactive props + characters + feedback + UI
```

Do not solve this by globally shipping every possible final prop.

---

# 8. Permanent visual rules

- Rich authoring-time composition; economical runtime rendering.
- Reuse does not mean clone-everywhere reuse.
- Specialized Activity art is expected to remain Activity-local.
- Theme bundles are provenance/source pools, not the primary authoring taxonomy.
- Newer does not automatically replace older.
- Useful variants can coexist under distinct semantic IDs.
- Do not create duplicate generic assets before checking all source pools.
- Producing-agent prose is not visual evidence; inspect actual pixels.

---

# 9. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this content-authoring work closes, reorders or bypasses R7.

No physical Acer/Pi acceptance should be claimed unless actually performed.
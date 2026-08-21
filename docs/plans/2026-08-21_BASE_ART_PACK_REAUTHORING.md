# Greia Generic Visual Toolbox Production — Maintainer-Side Plan

**Status:** ACTIVE CONTENT-PRODUCTION TRACK  
**Date:** 2026-08-21  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Purpose

Use the owner's local maintainer agent, where useful, to improve Greia's bundled **generic visual toolbox**.

This maintainer agent's drawing ability is not a Greia dependency and is not evidence about arbitrary future Activity-authoring agents.

The user/developer-facing workflow remains owned by:

`skills/greia-visual-authoring/SKILL.md`

## 2. Authoring architecture

Do not organize future toolbox work primarily as themed packs such as Clinic, Classroom, Fantasy Village, or Pond.

Theme/source bundles are provenance pools. The primary authoring interface is the generic semantic library:

1. Nature & Landscape
2. Interiors & Architecture
3. Furniture & Storage
4. Everyday Props & Containers
5. Making, Learning & Play
6. Lighting, Atmosphere, FX & Shadows
7. Shared UI
8. Canonical Characters

Authority:

`docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`

## 3. Established source pools

### Forest / Meadow v0.3

Promoted source pool with 28 semantic roles: 23 reauthored roles + 5 retained legacy roles + 2 preferred ingredients.

### Workshop v0.2

Promoted source pool with 24 finished semantic assets: 14 direct reauthored replacements + 5 retained baseline variants + 5 candidate coexistence variants + 2 preferred ingredients.

### Clinic / Care candidate

Useful reviewed source pool. It is **not** a core generic pack. Generic furniture/interior/comfort/container assets are harvested by reference; strongly medical props remain specialized.

### Reading / Classroom, Fantasy / Village / Night, Water / Pond

These remain source/provenance pools. Their generic assets have now been harvested/classified rather than treated as required theme packs.

## 4. Generic library consolidation and full source harvest

Commit `cc1d7f1` created the first six semantic indexes under:

`assets/visual/authoring_library/`

The first consolidation was incomplete because it omitted Reading/Classroom, Fantasy/Village/Night, and Water/Pond.

Commit `2dcf306` completed the full source harvest across those remaining environment/theme pools.

Current indexed state reported by the harvest:

```text
52 preferred finished assets
32 candidate-reference finished assets
5 authoring ingredients
89 total indexed reusable resources
```

The full harvest is owner-reviewed in:

`docs/reviews/visual/2026-08-21_generic-authoring-library-full-source-harvest/PRIMARY_REVIEW.md`

## 5. Accepted gap model

Every coverage question must distinguish:

```text
TRUE_MISSING
QUALITY_GAP
VARIETY_GAP
NO_GAP
```

The current audit supports these important findings:

- doors / room openings — `TRUE_MISSING`;
- standard dining/desk chair — `TRUE_MISSING`;
- books/storybooks — `QUALITY_GAP`;
- soft reading chair / bookcase — `QUALITY_GAP`;
- potted plant / basket — `QUALITY_GAP`;
- water botanical/structure roles — `QUALITY_GAP`;
- generic bridge/sign/well/lantern — `QUALITY_GAP`;
- basic tableware — `TRUE_MISSING`;
- generic mechanical/manipulative components — materially under-covered / `TRUE_MISSING` at component level.

## 6. Permanent composability rule

The generic library must not become an encyclopedia of arbitrary pre-finished clip-art nouns.

Prioritize **cross-Activity authoring leverage**.

> **Generic assets should encode reusable form; Activity-specific meaning and contents should remain separable whenever practical.**

Examples:

- empty plate rather than plate-with-toast as the only plate;
- empty bowl rather than cereal permanently baked in;
- books without readable titles or one fixed story;
- blank sign/board surfaces where text is Activity/localization-owned;
- generic gear/dial/lever components rather than one narrowly themed machine;
- source-level ingredients where they genuinely help agents compose bespoke Activity art.

This does not mean runtime fragment explosion. Source art may be composable during authoring and flattened for efficient runtime use.

## 7. Generic authoring-library admission state

The semantic index structure is canonical. Individual resources expose quality/admission state:

```text
preferred
candidate_reference
```

- `preferred` resources are reviewed strongly enough to be tried first for direct REUSE.
- `candidate_reference` resources may support COMPOSE/ADAPT or inspiration, but are not owner-approved preferred finished assets.

Newly produced generic assets start as `candidate_reference` until owner pixel review.

## 8. Production workflow

For future generic batches:

1. start from the full inventory/gap audit;
2. rank cross-Activity usefulness and composability, not theme completeness;
3. mix categories when that creates a stronger toolbox;
4. create roughly 12–18 assets at pack scale unless a smaller set is more coherent;
5. prefer semantically neutral/reusable forms over baked one-off contents;
6. create source-level ingredients only when they materially help Activity authors;
7. inspect actual pixels and representative child-facing sizes;
8. promote only the strongest resources into `preferred` status;
9. preserve source provenance without duplication;
10. do not touch runtime architecture merely to prove source art.

## 9. Current exact production gate

The full source harvest is complete.

Execute:

`docs/testing/2026-08-21_GENERIC_CORE_ESSENTIALS_BATCH_A.md`

This is the first authorized **new generic source-art batch** after consolidation.

It deliberately targets high-leverage gaps across:

- doors/openings;
- standard/soft seating;
- bookcase/books;
- plant/basket;
- neutral tableware;
- generic mechanical components.

It is not a kitchen/classroom/clinic theme pack.

## 10. Relationship to the user-agent skill

The maintainer track builds the toolbox.

Arbitrary Activity agents should conceptually:

```text
inventory Activity needs
→ search generic semantic library
→ prefer reviewed/preferred assets where they fit
→ inspect candidate/source references when useful
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local final art
→ flatten/build runtime rendition
→ integrate through Greia package/scene seams
→ visually review
```

The generic toolbox helps; it does not remove the expectation that specialized Activity art may need to be created locally.

## 11. Explicit drift to avoid

Do not:

- return to theme-by-theme pack production;
- create a giant noun warehouse merely to increase counts;
- bake arbitrary food/text/story meaning into otherwise generic resources;
- duplicate weak old assets without a quality reason;
- treat candidate references as preferred merely because they are indexed;
- infer arbitrary user-agent capability from the maintainer agent;
- reopen hero-tree specimen optimization;
- create a second runtime catalogue/cache architecture.

## 12. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content track closes, reorders, or bypasses R7.

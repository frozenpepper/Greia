# Greia Generic Visual Toolbox Production — Maintainer-Side Plan

**Status:** ACTIVE CONTENT-PRODUCTION / AUTHORING-TOOLING TRACK  
**Date:** 2026-08-22  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Purpose

Use the owner's local maintainer agent, where useful, to improve Greia's bundled **generic visual toolbox** and its authoring-time discoverability.

The maintainer agent's drawing ability is not a Greia dependency and is not evidence about arbitrary future Activity-authoring agents.

The user/developer-facing workflow remains owned by:

`skills/greia-visual-authoring/SKILL.md`

## 2. Authoring architecture

Do not organize toolbox work primarily as themed packs such as Clinic, Classroom, Fantasy Village, or Pond.

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

These remain source/provenance pools. Their generic assets have been harvested/classified rather than treated as required theme packs.

## 4. Generic library consolidation and full source harvest

Commit `cc1d7f1` created the first six semantic indexes under:

`assets/visual/authoring_library/`

Commit `2dcf306` completed the full source harvest across Reading/Classroom, Fantasy/Village/Night and Water/Pond.

Harvest state before Batch A admission:

```text
52 preferred finished assets
32 candidate-reference finished assets
5 authoring ingredients
89 total indexed reusable resources
```

Owner review:

`docs/reviews/visual/2026-08-21_generic-authoring-library-full-source-harvest/PRIMARY_REVIEW.md`

## 5. Accepted gap model

Every coverage question must distinguish:

```text
TRUE_MISSING
QUALITY_GAP
VARIETY_GAP
NO_GAP
```

An existing weak asset is a quality gap, not missing inventory.

## 6. Permanent composability rule

The generic library must not become an encyclopedia of arbitrary pre-finished clip-art nouns.

> **Generic assets should encode reusable form; Activity-specific meaning and contents should remain separable whenever practical.**

Examples:

- empty plate/bowl rather than food permanently baked in;
- books without readable titles or one fixed story;
- blank signs/boards where Activity/localization owns text;
- reusable gear/dial/lever components rather than one narrowly themed machine;
- source-level ingredients only when they genuinely improve authoring leverage.

Runtime remains economical: rich source work may be flattened into efficient runtime assets.

## 7. Generic authoring-library admission state

The semantic index structure is canonical. Individual resources expose:

```text
preferred
candidate_reference
```

- `preferred` → strong enough to consider first for direct REUSE.
- `candidate_reference` → useful for COMPOSE/ADAPT/reference, but not owner-approved first-choice direct-use art.

The purpose of these states is to avoid endless redraw loops merely to force every useful source into `preferred`.

## 8. Generic Core Essentials Batch A — reviewed

Candidate commit:

`574f19530ee292a81225ff14c09ad8b35f6cf933`

Actual owner-transfer PNGs were inspected.

Primary review:

`docs/reviews/visual/2026-08-21_generic-core-essentials-batch-a/PRIMARY_REVIEW.md`

Owner disposition:

```text
9 finished assets → preferred
7 finished assets → candidate_reference
2 authoring ingredients → preferred
```

Preferred finished assets:

- closed timber door;
- simple timber arch opening;
- spindle-back chair;
- tall open bookcase;
- empty woven basket;
- empty ceramic bowl;
- ceramic cup/saucer;
- interlocking gear pair;
- blank radial dial/hands.

Candidate references retained without redraw:

- ajar door;
- soft armchair;
- open picture book;
- mixed book stack;
- potted fern;
- empty ceramic plate;
- single `wooden` gear.

Important: **do not run a Batch A per-object finalization loop.** The weaker items are still useful references and can be reauthored later only when actual Activity demand justifies it.

## 9. Current exact gate

`docs/testing/2026-08-22_GENERIC_VISUAL_LIBRARY_ADMISSION_AND_DISCOVERY_TOOLING.md` is **EXECUTED**.

Accomplished:

1. Materialized the 9+2 owner-authorized preferred Batch A resources under stable generic source provenance (`assets/visual/generic/core_essentials/v0.1/`);
2. Kept the 7 weaker resources as candidate references (`assets/visual/pack_candidates/generic_core_essentials/2026-08-21/`);
3. Updated the six generic semantic indexes under `assets/visual/authoring_library/`;
4. Added the deterministic authoring-time discovery helper `tools/visual_authoring_library.py` (`collections`, `list`, `search`, `show`, `validate`);
5. Tested discovery tooling with pytest in `tests/test_visual_authoring_library.py`;
6. Updated `skills/greia-visual-authoring/SKILL.md` to guide arbitrary Activity-authoring agents;
7. Preserved runtime architecture boundaries (no new runtime consumers or catalogue changes).

No Batch B is currently authorized.

## 10. Why discovery tooling comes next

The toolbox now has enough breadth that the bottleneck is no longer raw asset count.

An arbitrary Activity-authoring agent should not need to:

- know historical theme folder names;
- manually grep six TOMLs;
- guess which source is preferred versus merely a candidate reference.

The next product value is a simple authoring-time query/list/show interface exposing semantic ID, collection, status, source path, tags/role and notes.

This tooling must remain deterministic, local and separate from Greia runtime architecture.

## 11. Relationship to the user-agent skill

The maintainer track builds and curates the toolbox.

Arbitrary Activity agents should conceptually:

```text
inventory Activity needs
→ query the generic semantic library
→ prefer reviewed/preferred assets where they fit
→ inspect candidate/source references when useful
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local final art
→ flatten/build runtime rendition
→ integrate through Greia package/scene seams
→ visually review
```

The toolbox helps; it does not remove the expectation that specialized Activity art may need to be created locally.

## 12. Explicit drift to avoid

Do not:

- return to theme-by-theme pack production;
- immediately create Batch B merely to increase asset count;
- redraw every candidate reference until it becomes preferred;
- create a giant noun warehouse;
- bake arbitrary food/text/story meaning into generic bases;
- infer arbitrary user-agent capability from the maintainer agent;
- reopen hero-tree specimen optimization;
- create a second runtime catalogue/cache architecture.

## 13. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content/authoring-tooling track closes, reorders, or bypasses R7.

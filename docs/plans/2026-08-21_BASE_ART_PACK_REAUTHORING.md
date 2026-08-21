# Greia Generic Visual Toolbox Production — Maintainer-Side Plan

**Status:** ACTIVE CONTENT-PRODUCTION TRACK  
**Date:** 2026-08-21  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Purpose

Use the owner's local maintainer agent, where useful, to improve Greia's bundled **generic visual toolbox**.

Its drawing ability is not a Greia dependency and is not evidence about arbitrary future Activity-authoring agents.

The user/developer-facing workflow remains owned by:

`skills/greia-visual-authoring/SKILL.md`

## 2. Architecture correction already established

Do not organize future authoring work primarily as themed packs such as Clinic, Classroom, Fantasy Village, or Pond.

Theme/source bundles are provenance pools. The primary Activity-authoring interface is the generic semantic library:

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

## 3. Strong source pools already established

### Forest / Meadow v0.3

Promoted source pool:

```text
28 semantic roles
= 23 reauthored roles
+ 5 deliberately retained legacy roles
+ 2 preferred authoring ingredients
```

### Workshop v0.2

Promoted source pool:

```text
24 finished semantic assets
= 14 direct reauthored replacements
+ 5 retained baseline variants
+ 5 candidate coexistence variants
+ 2 preferred authoring ingredients
```

### Clinic / Care candidate

Useful reviewed source pool. It is **not** a core generic pack. Broad furniture/interior/comfort/container assets may feed generic indexes; strongly medical props remain specialized.

## 4. First generic consolidation — structurally useful, coverage incomplete

Commit `cc1d7f1` created the first six semantic indexes and harvested Forest, Workshop and Clinic.

That structural step is accepted.

However, its gap report is **not authoritative** because it did not harvest existing:

- Reading / Classroom v0.1;
- Fantasy / Village / Night v0.1;
- Water / Pond v0.1.

This omission produced false “missing” conclusions. Reading/Classroom already contains books, a reading chair, potted plant, toy basket, bookcase, cushions, etc. Water/Pond already contains reusable water/reed/dock/stepping-stone/FX assets. Fantasy contains reusable bridge/signpost/well/lantern/cobblestone candidates.

Primary review:

`docs/reviews/visual/2026-08-21_generic-authoring-library-consolidation/PRIMARY_REVIEW.md`

## 5. Mandatory full-source harvest before drawing more

Do **not** start the previously proposed 16-asset Living & Learning batch yet.

Current exact gate:

`docs/testing/2026-08-21_GENERIC_VISUAL_LIBRARY_FULL_SOURCE_HARVEST.md`

It must inspect all remaining source pools and classify assets as:

```text
PREFERRED_GENERIC
CANDIDATE_GENERIC
REAUTHOR_GENERIC
SPECIALIZED_THEME_ONLY
DUPLICATE_OR_SUPERSEDED
UNRESOLVED
```

Then recompute every gap as:

```text
TRUE_MISSING
QUALITY_GAP
VARIETY_GAP
NO_GAP
```

## 6. Generic authoring-library admission state

The semantic index structure is canonical, but individual resources must expose their quality/admission state.

Use a simple field such as:

```toml
library_status = "preferred"
```

or:

```toml
library_status = "candidate_reference"
```

Activity agents should try preferred resources first for direct REUSE. Candidate references may still be useful for COMPOSE/ADAPT or inspiration.

Do not call all indexed resources equally canonical merely because they are discoverable.

## 7. Production workflow after full harvest

Only after the full source audit:

1. rank `TRUE_MISSING`, `QUALITY_GAP`, and important `VARIETY_GAP` roles;
2. choose the highest-value cross-Activity batch;
3. create roughly 12–18 assets at pack scale, unless a smaller batch is clearly better;
4. review actual pixels and runtime-size readability;
5. promote only the strongest resources into `preferred` generic status;
6. preserve source provenance without duplication.

Do not choose a batch because assets happen to belong to one old theme.

## 8. Examples of why harvest comes first

Before producing new books/chairs/plants, inspect:

`assets/visual/environments/reading_classroom/v0.1/`

Before producing new water/reeds/dock/pond FX, inspect:

`assets/visual/environments/water_pond/v0.1/`

Before producing generic bridge/sign/well/lantern/cobblestone resources, inspect:

`assets/visual/environments/fantasy_village_night/v0.1/`

An existing weak asset is a `QUALITY_GAP`, not a `TRUE_MISSING` asset.

## 9. Visual quality standard

Target:

- polished storybook / toy-diorama quality;
- strong child-readable silhouettes;
- broad semantic usefulness;
- coherent materials and lighting;
- clean alpha and convincing grounding;
- controlled detail;
- useful variation without style drift.

Reject:

- crude primitives;
- duplicate production caused by incomplete inventory;
- specialized assets cluttering the generic core;
- misleading semantic labels;
- false “missing” claims where an unindexed source already exists;
- local-agent-specific drawing recipes embedded into user-facing architecture;
- prose-only quality claims.

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

## 11. Exact current action

Execute only:

`docs/testing/2026-08-21_GENERIC_VISUAL_LIBRARY_FULL_SOURCE_HARVEST.md`

No new generic asset production is authorized before that audit is complete.

## 12. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content track closes, reorders or bypasses R7.
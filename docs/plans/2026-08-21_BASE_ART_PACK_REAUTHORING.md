# Greia Generic Visual Toolbox Production — Maintainer-Side Plan

**Status:** ACTIVE CONTENT-PRODUCTION TRACK  
**Date:** 2026-08-21  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Purpose

The owner's local agent is a maintainer-side art-production tool. The goal is to use it where useful to improve Greia's bundled **generic visual toolbox**.

Its drawing ability is not a dependency of Greia and is not evidence about arbitrary future Activity-authoring agents.

The generic Activity-agent workflow is owned separately by:

```text
skills/greia-visual-authoring/SKILL.md
```

## 2. Critical correction

The earlier content plan drifted into reauthoring historical themed bundles one-by-one:

```text
Forest / Meadow
Workshop
Clinic / Care
Reading / Classroom
Fantasy / Village / Night
Water / Pond
```

That sequence is no longer authoritative as a core-pack roadmap.

Themed bundles are useful source/provenance pools, but a specialized theme such as `Clinic / Care` is not automatically universal enough to deserve a maintained core pack.

The primary authoring interface must be **generic semantic collections** that can reference assets from many source bundles.

Authority:

```text
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
```

## 3. Established source-art results

### Forest / Meadow v0.3

Promoted source bundle:

```text
28 semantic roles
= 23 reauthored roles
+ 5 deliberately retained legacy roles
+ 2 preferred authoring ingredients
```

This is a strong source pool for `Nature & Landscape` and cross-cutting light/FX resources.

### Workshop v0.2

Promoted source bundle:

```text
24 finished semantic assets
= 14 direct reauthored replacements
+ 5 retained baseline variants
+ 5 candidate coexistence variants

2 preferred authoring ingredients
```

This is a strong source pool for interiors, furniture, storage, creative/learning props and lighting.

### Clinic / Care candidate

The 17-role candidate contains useful art, but **Clinic / Care is not authorized as the next core generic pack**.

Treat it as a source pool. Harvest broadly reusable pieces into generic indexes; keep strongly medical assets specialized/provenance-only unless later Activity demand justifies a domain extension.

Do not materialize `clinic/v0.2` merely because the candidate exists.

## 4. Core generic authoring collections

The current target taxonomy is:

1. **Nature & Landscape**
2. **Interiors & Architecture**
3. **Furniture & Storage**
4. **Everyday Props & Containers**
5. **Making, Learning & Play**
6. **Lighting, Atmosphere, FX & Shadows**
7. **Shared UI**
8. **Canonical Characters**

The first six should be exposed through cross-pack semantic indexes under:

```text
assets/visual/authoring_library/
```

These indexes reference source files; they do not duplicate them.

## 5. Production workflow

### 5.1 Consolidate before drawing more

Before creating more art:

1. index reviewed/promoted Forest/Meadow assets generically;
2. index reviewed/promoted Workshop assets generically;
3. classify Clinic candidate assets as generic vs specialized;
4. identify actual generic coverage gaps.

Current runbook:

```text
docs/testing/2026-08-21_GENERIC_VISUAL_LIBRARY_CONSOLIDATION.md
```

### 5.2 Produce missing generic families, not arbitrary themes

After consolidation, create the highest-value missing generic asset batch.

Potential broad gaps may include:

- doors / arches / room dividers;
- chairs / benches / seating variants;
- baskets / cups / plates / jars / boxes;
- books / paper / cards / boards;
- fabric / blanket / pillow pieces;
- generic mechanical pieces / knobs / gears;
- signs / boards without baked text;
- water-edge / reeds / splashes;
- toys / play objects;
- indoor plants;
- decorative trim;
- additional light/shadow forms.

Do not choose the next batch from an old theme name. Choose it from broad cross-Activity usefulness.

### 5.3 Preserve source provenance

Do not overwrite source bundles. Generic indexes should point to versioned source files and record provenance.

### 5.4 Keep useful variation

The strongest toolbox may expose several genuinely different assets for the same broad family, for example:

```text
open shelf vs cubby shelf
loose blocks vs block house
simple lamp vs articulated lamp
narrow beam vs wide beam
```

Distinct objects get distinct generic semantic IDs.

### 5.5 Promote ingredients selectively

Reusable source fragments are valuable only when they help Activity authors compose bespoke art.

Do not promote fragments merely because they were generated.

### 5.6 Review actual pixels

For new visual batches:

- inspect assets individually;
- test representative child-facing sizes;
- inspect one or more neutral compositions;
- use owner ZIP evidence where requested;
- reject prose-only quality claims.

## 6. Quality standard

Target:

- polished storybook / toy-diorama quality;
- strong child-readable silhouettes;
- useful broad semantic roles;
- coherent materials and lighting;
- clean alpha;
- convincing grounding;
- controlled detail;
- composability;
- variation without style drift.

Reject:

- crude primitives;
- assets so theme-specific they are unlikely to help unrelated Activities, unless deliberately kept as an optional specialized extension;
- duplicate near-identical variants;
- misleading semantic labels;
- giant source libraries that require users to know historical scene names;
- forced one-for-one replacement;
- arbitrary runtime discovery;
- local-agent-specific SVG recipes embedded in user-facing architecture.

## 7. Relationship to themed source bundles

Existing themed folders remain useful for:

- provenance;
- visual references;
- compositions;
- source files;
- optional specialized extensions.

They are not deleted.

But future Activity authors should generally discover reusable assets through generic indexes first.

Example:

```text
historical source:
assets/visual/environments/clinic/.../cabinet.svg

primary author discovery:
furniture/storage semantic index → cabinet
```

Likewise a medical-specific stethoscope may remain specialized rather than entering the core generic toolbox.

## 8. Promotion policy

For source-art review, the permanent dispositions remain useful:

```text
CANDIDATE_REPLACES
BASELINE_RETAINS
KEEP_BOTH_DISTINCT
UNRESOLVED
```

For generic-library admission, use:

```text
GENERIC_INDEX
SPECIALIZED_THEME_ONLY
UNRESOLVED
```

A source asset can be visually good and still be too specialized for the generic core.

## 9. Relationship to the user-agent skill

The maintainer track produces the toolbox.

The generic skill teaches arbitrary agents how to use it:

```text
inventory Activity needs
→ search generic semantic authoring library
→ inspect source/reference art
→ REUSE, COMPOSE/ADAPT, or CREATE ORIGINAL
→ create Activity-local final art
→ flatten/build runtime rendition
→ integrate through Greia package/scene seams
→ visually review
```

Do not assume user agents can reproduce maintainer-agent artwork.

## 10. Exact current action

Stop Clinic/Care promotion/finalization as a core-pack task.

Execute:

```text
docs/testing/2026-08-21_GENERIC_VISUAL_LIBRARY_CONSOLIDATION.md
```

That task must:

- create the generic authoring-library indexes;
- map Forest/Meadow and Workshop into them;
- harvest broadly reusable Clinic candidate assets by reference;
- keep medical-specific assets specialized;
- produce a generic coverage-gap report;
- recommend the next **generic** art-production batch.

After that, produce missing generic resources by broad usefulness rather than continuing blindly to Reading/Classroom, Fantasy/Village/Night, or Water/Pond.

## 11. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual content track closes, reorders or bypasses R7.

Source-art organization does not authorize physical/runtime claims that have not been tested.

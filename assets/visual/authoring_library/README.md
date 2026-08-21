# Greia Generic Visual Authoring Library

**Status:** Canonical semantic discovery structure; resource admission still being completed  
**Date:** 2026-08-21  
**Parent Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Taxonomy Reference:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**User-Agent Guidance:** `skills/greia-visual-authoring/SKILL.md`

## Overview

The Generic Visual Authoring Library is the primary discovery interface for Activity authors in the Greia ecosystem.

Instead of forcing authors to guess which historical theme/source folder contains a useful asset, this library organizes reusable visual resources by **what they are and what role they serve**.

The **semantic discovery structure is canonical**. Individual resources are not automatically equal in quality/admission state merely because they appear in an index.

Each indexed resource should expose an authoring-library status such as:

```text
preferred
candidate_reference
```

Use `preferred` resources first for direct REUSE. `candidate_reference` resources may still be valuable for COMPOSE/ADAPT or as visual reference, but should not be treated as owner-approved canonical finished art.

Specialized theme/domain assets remain available from their source/provenance bundles and should not clutter the primary generic core.

## Structure

The library is partitioned into six core semantic collections:

1. [`nature_landscape.toml`](nature_landscape.toml) — Botanical, terrain, water, and outdoor horizon assets.
2. [`interiors_architecture.toml`](interiors_architecture.toml) — Walls, floors, windows, drapery, rugs, doors/openings, and broad room features.
3. [`furniture_storage.toml`](furniture_storage.toml) — Tables, seating, daybeds, shelving, cabinets, pegboards, and storage.
4. [`everyday_props.toml`](everyday_props.toml) — Lamps, cushions, containers, bottles, basins, baskets, paper objects, and other broadly reusable props.
5. [`making_learning_play.toml`](making_learning_play.toml) — Easels, palettes, brushes, blocks, books/reading props, and generic toys/play objects.
6. [`lighting_fx_shadows.toml`](lighting_fx_shadows.toml) — Sunbeams, window light shafts, fog, particles, contact shadows, and generic feedback/ambient FX.

Shared UI and Canonical Characters remain separate stricter resource families rather than being forced into these six environment/prop indexes.

## Source bundles currently referenced

- **Forest / Meadow v0.3:** `assets/visual/environments/forest_meadow/v0.3/` — promoted source pool.
- **Workshop v0.2:** `assets/visual/environments/workshop/v0.2/` — promoted source pool.
- **Clinic / Care 2026-08-21 Candidate:** `assets/visual/pack_candidates/clinic/2026-08-21/` — reviewed source pool; generic entries derived from it must carry non-promoted/candidate status unless separately approved.

## Incomplete harvest warning

Do not treat the current inventory/counts as final coverage authority yet.

Existing source pools still requiring full generic harvest/classification include:

- `assets/visual/environments/reading_classroom/v0.1/`
- `assets/visual/environments/fantasy_village_night/v0.1/`
- `assets/visual/environments/water_pond/v0.1/`

The authoritative completion gate is:

`docs/testing/2026-08-21_GENERIC_VISUAL_LIBRARY_FULL_SOURCE_HARVEST.md`

Until that gate is complete, a role omitted from these indexes is not automatically a true missing asset.

## Finished assets versus authoring ingredients

Keep these counts separate:

- **finished assets** are complete reusable visual objects;
- **authoring ingredients** are source-level pieces intended to help agents compose/adapt bespoke Activity-local art.

Both are useful resources, but ingredients should not be described as interchangeable runtime-ready finished assets.

## Discovery rule for Activity authors

Conceptually:

```text
Activity visual need
→ search generic semantic indexes
→ prefer reviewed/preferred finished assets when they genuinely fit
→ inspect candidate/reference assets and source packs when useful
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local runtime-ready result
```

Do not force an unsuitable shared asset merely because it exists.
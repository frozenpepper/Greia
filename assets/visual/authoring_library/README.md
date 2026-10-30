# Greia Generic Visual Authoring Library

**Status:** Canonical Authoring-Library Index  
**Date:** 2026-08-22  
**Parent Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Taxonomy Reference:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Audit Reference:** `PRIMARY_REVIEW.md` (archived; see git history)  
**Discovery Tooling:** `tools/visual_authoring_library.py`  
**User-Agent Guidance:** `skills/greia-visual-authoring/SKILL.md`

## Overview

The Generic Visual Authoring Library is the primary discovery interface for Activity authors in the Greia ecosystem. Instead of forcing authors to guess which historical theme folder contains a useful asset, this library organizes high-craft, reviewed source assets by **what they are and what role they serve**.

## Admission & Quality Status Model

Every indexed asset explicitly declares its `library_status`:

- `library_status = "preferred"` (57 finished assets, 7 ingredients): Fully owner-reviewed and promoted assets (from Forest/Meadow v0.3, Workshop v0.2, and Core Essentials v0.1). **Use these first for direct `REUSE`.**
- `library_status = "candidate_reference"` (37 finished assets, 0 ingredients): High-value candidate references (from Core Essentials Batch A candidates, Clinic candidate, Water/Pond v0.1, Reading v0.1, and Fantasy v0.1). Useful for `COMPOSE / ADAPT` and provisional composition.

> [!NOTE]
> Specialized themed props (medical tools, fantasy castles, specialized cottage architecture) and legacy assets identified as Quality Gaps (`REAUTHOR_GENERIC`) remain in their source bundles and are not indexed as preferred generic library assets.

## Collections

1. [`nature_landscape.toml`](nature_landscape.toml) — Botanical, terrain, water, night sky, and outdoor horizon assets (21 preferred, 6 candidate references, 2 ingredients).
2. [`interiors_architecture.toml`](interiors_architecture.toml) — Walls, floors, windows, archways, doors, drapes, rugs, and room bunting (6 preferred, 5 candidate references, 1 ingredient).
3. [`furniture_storage.toml`](furniture_storage.toml) — Tables, seating, daybeds, shelving, pegboards, cabinets, bookcases, and storage crates (8 preferred, 4 candidate references, 1 ingredient).
4. [`everyday_props.toml`](everyday_props.toml) — Tools, storage baskets, jars, tableware, books, containers, botanicals, and small items (7 preferred, 7 candidate references, 1 ingredient).
5. [`making_learning_play.toml`](making_learning_play.toml) — Art supplies, manipulative toys, mechanisms, clocks, plushies, and play structures (6 preferred, 4 candidate references, 2 ingredients).
6. [`lighting_fx_shadows.toml`](lighting_fx_shadows.toml) — Sunbeams, moonbeams, window light, water ripples, ambient particles, contact shadows, and feedback FX (9 preferred, 11 candidate references, 0 ingredients).

Totals:

```text
57 preferred finished assets
37 candidate-reference finished assets
7 preferred authoring ingredients
101 indexed reusable visual resources
```

## Source Pools Referenced
- **Core Essentials v0.1:** `assets/visual/generic/core_essentials/v0.1/` (promoted preferred)
- **Forest / Meadow v0.3:** `assets/visual/environments/forest_meadow/v0.3/` (promoted preferred)
- **Workshop v0.2:** `assets/visual/environments/workshop/v0.2/` (promoted preferred)
- **Core Essentials Batch A Candidates:** `assets/visual/pack_candidates/generic_core_essentials/2026-08-21/` (candidate references)
- **Clinic / Care Candidate:** `assets/visual/pack_candidates/clinic/2026-08-21/` (reviewed candidate references)
- **Water / Pond v0.1:** `assets/visual/environments/water_pond/v0.1/` (candidate references)
- **Fantasy / Village / Night v0.1:** `assets/visual/environments/fantasy_village_night/v0.1/` (candidate references)
- **Reading / Classroom v0.1:** `assets/visual/environments/reading_classroom/v0.1/` (candidate references)

## Discovery CLI Tooling

Use `tools/visual_authoring_library.py` to search and inspect library assets:

```bash
# List all collections
python tools/visual_authoring_library.py collections

# Search for assets
python tools/visual_authoring_library.py search chair
python tools/visual_authoring_library.py search "book storage" --status preferred

# Show full metadata for an asset
python tools/visual_authoring_library.py show furniture.seating.chair.spindle_wood

# Validate structure across all library TOMLs
python tools/visual_authoring_library.py validate
```

## Offline visual browser (developer tooling)

The CLI and visual browser use exactly the same six TOML indexes. To view actual
source-master SVG artwork as large cards with search/status/category filters:

```bash
mkdir -p tmp
python3 tools/visual_authoring_library.py gallery --output tmp/greia-visual-library.html
# Open tmp/greia-visual-library.html in a normal development-host browser.
```

Output must be new (never overwritten implicitly), is entirely local, uses
relative paths back into the project, rejects escaped/missing sources, loads
no remote scripts/fonts/CDNs, and never becomes part of the Greia child image.
The gallery is a **selection aid**, not runtime art admission or visual-quality
certification. Preserve SVG masters, confirm final rendered art at 128/64 px and
run the normal visual acceptance procedure before promoting a candidate.

**2026-10-08 discovery clarification:** The `component.mechanical.dial_hands.blank`
and `ingredient.mechanical.axle_hands` resources already carry the
`clock` semantic tag. The generated gallery now displays human-readable
role labels, original canonical IDs **and** source tags. Search matches
tags as well as names; a zero count for literal IDs containing `clock`
does not mean a zero search result. After checkout update, regenerate with
a fresh output filename before checking `clock`. Browser screenshot/
visual usability remains unaccepted when no browser is available.

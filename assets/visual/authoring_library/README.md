# Greia Generic Visual Authoring Library

**Status:** Canonical Authoring-Library Index  
**Date:** 2026-08-21  
**Parent Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Taxonomy Reference:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Audit Reference:** `docs/reviews/visual/2026-08-21_generic-authoring-library-full-source-harvest/FULL_SOURCE_AUDIT.md`  
**User-Agent Guidance:** `skills/greia-visual-authoring/SKILL.md`

## Overview

The Generic Visual Authoring Library is the primary discovery interface for Activity authors in the Greia ecosystem. Instead of forcing authors to guess which historical theme folder contains a useful asset, this library organizes high-craft, reviewed source assets by **what they are and what role they serve**.

## Admission & Quality Status Model

Every indexed asset explicitly declares its `library_status`:

- `library_status = "preferred"`: Fully owner-reviewed and promoted assets (from Forest/Meadow v0.3 and Workshop v0.2). **Use these first for direct `REUSE`.**
- `library_status = "candidate_reference"`: High-value candidate references (from Clinic candidate, Water/Pond v0.1, Reading v0.1, and Fantasy v0.1). Useful for `COMPOSE / ADAPT` and provisional composition.

> [!NOTE]
> Specialized themed props (medical tools, fantasy castles, specialized cottage architecture) and legacy assets identified as Quality Gaps (`REAUTHOR_GENERIC`) remain in their source bundles and are not indexed as preferred generic library assets.

## Collections

1. [`nature_landscape.toml`](nature_landscape.toml) — Botanical, terrain, water, night sky, and outdoor horizon assets.
2. [`interiors_architecture.toml`](interiors_architecture.toml) — Walls, floors, windows, drapery, rugs, and room bunting.
3. [`furniture_storage.toml`](furniture_storage.toml) — Tables, seating, daybeds, shelving, pegboards, and storage crates.
4. [`everyday_props.toml`](everyday_props.toml) — Lamps, cushions, containers, bottles, basins, paper stacks, and notes.
5. [`making_learning_play.toml`](making_learning_play.toml) — Easels, palettes, brushes, toy blocks, plush comfort toys, play tents, and hanging mobiles.
6. [`lighting_fx_shadows.toml`](lighting_fx_shadows.toml) — Sunbeams, moonbeams, window light, water ripples, ambient particles, contact shadows, and feedback FX.

## Source Bundles Referenced
- **Forest / Meadow v0.3:** `assets/visual/environments/forest_meadow/v0.3/` (promoted preferred)
- **Workshop v0.2:** `assets/visual/environments/workshop/v0.2/` (promoted preferred)
- **Clinic / Care 2026-08-21 Candidate:** `assets/visual/pack_candidates/clinic/2026-08-21/` (reviewed candidate references)
- **Water / Pond v0.1:** `assets/visual/environments/water_pond/v0.1/` (candidate references)
- **Fantasy / Village / Night v0.1:** `assets/visual/environments/fantasy_village_night/v0.1/` (candidate references)
- **Reading / Classroom v0.1:** `assets/visual/environments/reading_classroom/v0.1/` (candidate references)
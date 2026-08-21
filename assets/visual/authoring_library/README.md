# Greia Generic Visual Authoring Library

**Status:** Canonical Authoring-Library Index  
**Date:** 2026-08-21  
**Parent Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Taxonomy Reference:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**User-Agent Guidance:** `skills/greia-visual-authoring/SKILL.md`

## Overview

The Generic Visual Authoring Library is the primary discovery interface for Activity authors in the Greia ecosystem. Instead of forcing authors to guess which historical theme folder contains a useful asset, this library organizes high-craft, reviewed source assets by **what they are and what role they serve**.

## Structure

The library is partitioned into six core semantic collections:

1. [`nature_landscape.toml`](nature_landscape.toml) — Botanical, terrain, water, and outdoor horizon assets.
2. [`interiors_architecture.toml`](interiors_architecture.toml) — Walls, floors, windows, drapery, and rugs.
3. [`furniture_storage.toml`](furniture_storage.toml) — Tables, seating, daybeds, shelving, pegboards, and storage crates.
4. [`everyday_props.toml`](everyday_props.toml) — Lamps, cushions, containers, bottles, basins, paper stacks, and notes.
5. [`making_learning_play.toml`](making_learning_play.toml) — Easels, palettes, brushes, toy blocks, and plush comfort toys.
6. [`lighting_fx_shadows.toml`](lighting_fx_shadows.toml) — Sunbeams, window light shafts, fog, particles, contact shadows, and feedback FX.

## Source Bundles Referenced
- **Forest / Meadow v0.3:** `assets/visual/environments/forest_meadow/v0.3/` (promoted)
- **Workshop v0.2:** `assets/visual/environments/workshop/v0.2/` (promoted)
- **Clinic / Care 2026-08-21 Candidate:** `assets/visual/pack_candidates/clinic/2026-08-21/` (reviewed source pool)
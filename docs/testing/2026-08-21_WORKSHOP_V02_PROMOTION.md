# Workshop v0.2 — Exact Owner-Authorized Promotion Runbook

**Date:** 2026-08-21  
**Authority:** `docs/reviews/visual/2026-08-21_workshop-pack-finalization/PRIMARY_PROMOTION_REVIEW.md`  
**Candidate:** `assets/visual/pack_candidates/workshop/2026-08-21/`  
**Baseline:** `assets/visual/environments/workshop/v0.1/`

## 1. Purpose

Materialize the already-authorized Workshop v0.2 source toolbox. This is a mechanical promotion task, not another art pass.

Do not redesign, redraw, optimize, or reinterpret assets during this gate.

## 2. Create the promoted pack

Create:

```text
assets/visual/environments/workshop/v0.2/
```

Preserve `assets/visual/environments/workshop/v0.1/` unchanged as provenance.

The promoted pack must contain exactly the approved semantic toolbox from the primary promotion review.

## 3. Direct candidate replacements

Copy from the finalized candidate pack and expose under these semantic IDs:

```text
workshop.workbench
workshop.stool
workshop.easel
workshop.pegboard
workshop.storage.box
workshop.paint.palette
workshop.brush.bundle
workshop.pencil.cup
workshop.paint.jars
workshop.paper.stack
workshop.rug
workshop.window
workshop.wall.base
workshop.floor.base
```

## 4. Coexisting distinct variants

Materialize both members of each pair with distinct filenames/semantic IDs. Do not overwrite one with the other.

```text
workshop.shelf.open            ← candidate
workshop.shelf.cubby           ← v0.1 baseline

workshop.blocks.house          ← candidate
workshop.blocks.loose          ← v0.1 baseline

workshop.note.cork_tile        ← candidate
workshop.note.pinned           ← v0.1 baseline

workshop.desk_lamp.articulated ← candidate
workshop.desk_lamp.simple      ← v0.1 baseline

workshop.window_light.wide     ← candidate
workshop.window_light.narrow   ← v0.1 baseline
```

Use clear non-colliding filenames inside v0.2, e.g. `shelf_open.svg`, `shelf_cubby.svg`, etc.

## 5. Preferred authoring ingredients

Create:

```text
assets/visual/environments/workshop/v0.2/ingredients/
```

Promote exactly:

```text
ingredient.wood  → ingredients/ingredient_wood_joint.svg
ingredient.paint → ingredients/ingredient_paint_dabs.svg
```

Do not promote experimental candidate-internal note/light ingredients.

## 6. Catalog and metadata

Create/update within v0.2:

```text
catalog.toml
README.md
COMPOSITION.md
```

Requirements:

- catalog ID: `greia.environment.workshop.v0.2`
- status: `promoted`
- runtime_consumed: remain `false` unless already factually changed by unrelated work
- record source provenance per asset (`2026-08-21_candidate` or `legacy_v0.1_retained`)
- document the five coexistence pairs explicitly
- document recommended lamp use honestly: simple compact variant is stronger at very small sizes; articulated variant is intended for larger/detailed scene placement
- explain that the pack is an authoring toolbox, not a mandatory baked Workshop room
- list the two preferred ingredients separately from finished assets

## 7. Pack indexes

Update the source-pack index/metadata so Workshop v0.2 is the preferred Workshop authoring pack while v0.1 remains historical provenance.

Inspect current indexing before editing; do not invent a parallel registry.

## 8. Runtime boundary

Do not change merely to complete source promotion:

```text
assets/catalog/shared_visuals_v1_source.toml
assets/catalog/shared_visuals_v1.toml
src/greia_platform/*
activities/*
```

Source-pack promotion does not imply runtime promotion of every Workshop asset.

## 9. Verification

Verify mechanically:

1. v0.1 remains unchanged;
2. v0.2 exists with 24 finished semantic assets;
3. all five coexistence pairs have both distinct files/IDs;
4. exactly two preferred authoring ingredients are present;
5. catalog paths resolve inside v0.2;
6. no duplicate semantic IDs;
7. pack index points to v0.2 as preferred Workshop pack;
8. runtime catalogues/Activities were not changed by this promotion gate.

Do not run GitHub-hosted Actions.

## 10. Commit and return

Commit and push the exact promotion.

Return:

- commit SHA;
- promoted v0.2 path;
- finished semantic asset count;
- coexistence pair count;
- ingredient count;
- confirmation that v0.1 is preserved;
- confirmation that runtime consumers remain unchanged.

Then stop Workshop work and proceed to the Clinic / Care reauthoring runbook already present on `main`.

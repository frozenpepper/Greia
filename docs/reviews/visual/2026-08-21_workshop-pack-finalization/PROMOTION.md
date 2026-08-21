# Workshop Base Art Pack — Proposed v0.2 Promotion Proposal

**Date:** 2026-08-21  
**Pack Status:** Proposed for Owner Promotion Review  
**Parent Plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`  
**Review Runbook:** `docs/testing/2026-08-21_WORKSHOP_PACK_FINALIZATION.md`  
**Primary Review Reference:** `docs/reviews/visual/2026-08-21_workshop-base-pack-reauthoring/PRIMARY_REVIEW.md`

---

## 1. Executive Promotion Summary

In alignment with the owner disposition in `PRIMARY_REVIEW.md`, this proposal materializes the **strongest practical toolbox** rather than enforcing an arbitrary 19-for-19 replacement. Where baseline and candidate assets represent distinctly useful functional objects (e.g., open bracket shelf vs cubby cabinet; house blocks vs loose block pile; articulated lamp vs compact simple lamp), **both variants are preserved under clean, unambiguous semantic IDs**.

### Key Proposal Metrics

- **Total Proposed Finished Assets:** **24 Finished Assets** (across 24 distinct semantic roles)
- **Direct Candidate Replacements:** **14 Roles**
- **Retained Baseline Roles:** **5 Roles**
- **Meaningful Coexistence Pairs:** **5 Pairs** (10 assets total)
- **Unresolved Roles:** **0**
- **Preferred Authoring Ingredients:** **2** (`ingredient_wood_joint.svg`, `ingredient_paint_dabs.svg`)

---

## 2. Complete Proposed Inventory & Disposition Matrix

| Original Role ID | Proposed Semantic ID | Source | Disposition | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `workshop.workbench` | `workshop.workbench` | Candidate | `CANDIDATE_REPLACES` | Substantially better craftsman timber joinery, chamfered slab, drawer, turned brass knob, and splayed grounded legs. |
| `workshop.stool` | `workshop.stool` | Candidate | `CANDIDATE_REPLACES` | Turned dished seat with visible mortise stretchers and authentic wood construction. |
| `workshop.easel` | `workshop.easel` | Candidate | `CANDIDATE_REPLACES` | A-frame artist mast with height-adjustable canvas tray and painted meadow canvas. |
| `workshop.pegboard` | `workshop.pegboard` | Candidate | `CANDIDATE_REPLACES` | Perforated birch board with hanging wooden mallet, ruler, and twine loop. |
| `workshop.storage.box` | `workshop.storage.box` | Candidate | `CANDIDATE_REPLACES` | Plywood craft crate with finger-joint corners, cutout handholds, and brass label plate. |
| `workshop.shelf` | `workshop.shelf.open` | Candidate | `KEEP_BOTH_DISTINCT` | Open single-plank bracket shelf with jars and scroll, providing versatile background placement. |
| `workshop.shelf` | `workshop.shelf.cubby` | Baseline v0.1 | `KEEP_BOTH_DISTINCT` | Retained compact closed wall storage cabinet with structured compartments. |
| `workshop.paint.palette` | `workshop.paint.palette` | Candidate | `CANDIDATE_REPLACES` | Birch artist palette with volumetric 3D Gouache paint dollops and thumbhole. |
| `workshop.brush.bundle` | `workshop.brush.bundle` | Candidate (Rev) | `CANDIDATE_REPLACES` | Revised with 5 clustered brushes bound tightly with a leather/twine strap. |
| `workshop.pencil.cup` | `workshop.pencil.cup` | Candidate | `CANDIDATE_REPLACES` | Glazed teal ceramic studio mug with raw terracotta foot and sharpened colored pencils. |
| `workshop.paint.jars` | `workshop.paint.jars` | Candidate | `CANDIDATE_REPLACES` | Glass tempera jars with screw lids, transparency, and distinct color fill levels. |
| `workshop.blocks` | `workshop.blocks.house` | Candidate | `KEEP_BOTH_DISTINCT` | Deliberately assembled architectural block construction (arch, cube, prism roof). |
| `workshop.blocks` | `workshop.blocks.loose` | Baseline v0.1 | `KEEP_BOTH_DISTINCT` | Retained loose playful block stack for casual floor scatter. |
| `workshop.paper.stack` | `workshop.paper.stack` | Candidate (Rev) | `CANDIDATE_REPLACES` | Revised heavy watercolor paper ream with stepped layer lines and curling active top sketch. |
| `workshop.pinboard.note`| `workshop.note.cork_tile`| Candidate | `KEEP_BOTH_DISTINCT` | Cork-backed framed note tile with star doodle. |
| `workshop.pinboard.note`| `workshop.note.pinned` | Baseline v0.1 | `KEEP_BOTH_DISTINCT` | Retained lightweight pinned paper memo. |
| `workshop.desk.lamp` | `workshop.desk_lamp.articulated`| Candidate | `KEEP_BOTH_DISTINCT` | Articulated architect lamp with mint enamel shade and brass joints (recommended for >=128px scenes). |
| `workshop.desk.lamp` | `workshop.desk_lamp.simple` | Baseline v0.1 | `KEEP_BOTH_DISTINCT` | Retained compact goose-neck lamp with high readability at <=64px runtime icons. |
| `workshop.rug` | `workshop.rug` | Candidate | `CANDIDATE_REPLACES` | Concentric braided wool rag rug with visible perimeter stitching and warm tactile palette. |
| `workshop.window` | `workshop.window` | Candidate | `CANDIDATE_REPLACES` | Arched timber window frame looking onto sunny meadow with terracotta potted plant on sill. |
| `workshop.window.light`| `workshop.window_light.wide` | Candidate | `KEEP_BOTH_DISTINCT` | Broad atmospheric morning sunbeam shaft with floating dust motes. |
| `workshop.window.light`| `workshop.window_light.narrow`| Baseline v0.1 | `KEEP_BOTH_DISTINCT` | Retained narrow layered light beam for targeted focus highlighting. |
| `workshop.wall.base` | `workshop.wall.base` | Candidate | `CANDIDATE_REPLACES` | Warm plaster studio wall with horizontal wood wainscot chair-rail molding. |
| `workshop.floor.base` | `workshop.floor.base` | Candidate | `CANDIDATE_REPLACES` | Wide-plank golden oak studio flooring with subtle butt joints. |

---

## 3. Preferred Authoring Ingredients

1. `ingredient.wood` (`ingredients/ingredient_wood_joint.svg`) — Mortise, tenon, and dowel joint detail for furniture construction.
2. `ingredient.paint` (`ingredients/ingredient_paint_dabs.svg`) — Volumetric glossy 3D Gouache paint dollops for art props.
*(The experimental note and light shaft ingredients remain candidate-internal and are not proposed for base promotion.)*
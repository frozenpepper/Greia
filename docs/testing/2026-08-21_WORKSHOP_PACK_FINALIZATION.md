# Workshop Base Art Pack — Finalization and Promotion-Candidate Gate

**Date:** 2026-08-21  
**Purpose:** perform one bounded finalization pass on the already-strong Workshop candidate, optimize the resulting toolbox rather than force 19/19 replacement, and prepare owner promotion evidence.  
**Primary review:** `docs/reviews/visual/2026-08-21_workshop-base-pack-reauthoring/PRIMARY_REVIEW.md`  
**Baseline:** `assets/visual/environments/workshop/v0.1/`  
**Candidate:** `assets/visual/pack_candidates/workshop/2026-08-21/`

## 1. Scope

This is the **last Workshop authoring pass before promotion review**.

Do not reauthor the whole pack again. Do not polish already-good workbench/rug/window/crate/palette/etc. merely for marginal detail.

The owner review has already concluded:

- the candidate family is stronger overall than v0.1;
- a forced 19-for-19 replacement is the wrong objective;
- some baseline and candidate assets are actually different useful toolbox objects and should coexist under distinct semantic IDs.

Your task is only to:

1. resolve the few weak/misnamed candidate roles;
2. preserve meaningful baseline variants instead of deleting useful coverage;
3. define the exact proposed Workshop v0.2 inventory;
4. prepare complete visual evidence for owner promotion review.

After this gate, stop Workshop authoring and wait for promotion review.

---

## 2. Read first

Read:

```text
AGENTS.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
docs/reviews/visual/2026-08-21_workshop-base-pack-reauthoring/PRIMARY_REVIEW.md
assets/visual/environments/workshop/v0.1/catalog.toml
assets/visual/pack_candidates/workshop/2026-08-21/catalog.toml
```

Inspect the committed comparison images before making decisions.

---

## 3. Promotion philosophy: strongest toolbox, not highest replacement percentage

For every baseline/candidate pair, determine whether it is:

```text
CANDIDATE_REPLACES
BASELINE_RETAINS
KEEP_BOTH_DISTINCT
UNRESOLVED
```

`KEEP_BOTH_DISTINCT` is correct when old and new art are genuinely different useful objects, not near-duplicates.

Do not force a candidate into an old semantic ID when the candidate actually depicts a different object.

The promoted Workshop v0.2 may therefore contain **more than 19 finished assets**.

Do not inflate the pack with near-duplicates.

---

## 4. Already-strong direct candidates

Do not rework these unless a real rendering/package defect is discovered:

```text
workshop.workbench
workshop.stool
workshop.easel
workshop.pegboard
workshop.storage.box
workshop.paint.palette
workshop.pencil.cup
workshop.paint.jars
workshop.rug
workshop.window
workshop.wall.base
workshop.floor.base
```

They already establish the candidate's pack-level improvement.

---

## 5. Required distinct-variant decisions

### 5.1 Shelf

Baseline and candidate represent different useful furniture:

- baseline: compact cubby/cabinet-like wall storage;
- candidate: open single-plank bracket shelf.

Default direction: **KEEP_BOTH_DISTINCT**.

Use clear semantic IDs such as:

```text
workshop.shelf.open
workshop.shelf.cubby
```

Do not preserve ambiguous duplicate `workshop.shelf` IDs.

### 5.2 Blocks

Baseline and candidate represent different useful states:

- baseline: loose/piled blocks;
- candidate: assembled house/arch construction.

Default direction: **KEEP_BOTH_DISTINCT**.

Suggested IDs:

```text
workshop.blocks.loose
workshop.blocks.house
```

### 5.3 Pinboard note

Baseline is a lightweight pinned/sticky note. Candidate is a cork-backed/framed note tile.

If both remain visually useful, retain both under distinct semantics, e.g.:

```text
workshop.note.pinned
workshop.note.cork_tile
```

### 5.4 Window light

Baseline and candidate provide different beam shapes/composition behavior.

If both remain clean and useful, retain as distinct variants, e.g.:

```text
workshop.window_light.narrow
workshop.window_light.wide
```

Show them over the same dark/mid-value room patch so the owner can compare actual light behavior.

---

## 6. Required bounded correction/decision roles

### 6.1 Brush bundle

Current candidate does not read as a bundle; it reads as three separate brushes.

Choose one:

**A. Revise once** so the candidate genuinely reads as a coherent brush bundle/container at child-facing size; then it may replace baseline.

or

**B. Retain baseline** for:

```text
workshop.brush.bundle
```

and keep the current candidate only if useful under a distinct semantic role such as:

```text
workshop.brush.loose
```

Do not promote the current three-brush candidate unchanged under `workshop.brush.bundle`.

### 6.2 Paper stack

Current candidate reads more like a sketch sheet than a stack.

Choose one:

**A. Revise once** to produce a clearly layered, grounded paper-stack silhouette;

or

**B. Retain baseline** as:

```text
workshop.paper.stack
```

and preserve the candidate only if useful as a distinct:

```text
workshop.paper.sketch
```

### 6.3 Desk lamp

Candidate articulated lamp is attractive at larger size but nearly disappears in the 64 px proof.

Do not make a false universal replacement claim.

Either:

- retain both simple and articulated lamp variants; or
- retain baseline as compact/default lamp and candidate as articulated authoring variant.

Suggested semantics if both survive:

```text
workshop.desk_lamp.simple
workshop.desk_lamp.articulated
```

Create direct 192/128/96/64 px comparison evidence for both lamps. The 64 px result may legitimately show that one variant is not intended for that size, but the intended minimum size must be explicit.

---

## 7. Authoring ingredient decision

Current candidate ingredients:

```text
ingredient_wood_joint.svg
ingredient_paint_dabs.svg
ingredient_pinned_note.svg
ingredient_light_shaft.svg
```

Default likely promotion:

```text
ingredient_wood_joint.svg
ingredient_paint_dabs.svg
```

For `ingredient_pinned_note.svg` and `ingredient_light_shaft.svg`, keep only if they add clear reusable authoring value beyond the finished pack assets.

Do not promote ingredients merely because they exist.

---

## 8. Proposed v0.2 catalogue

Create a complete promotion proposal in:

```text
docs/reviews/visual/2026-08-21_workshop-pack-finalization/PROMOTION.md
docs/reviews/visual/2026-08-21_workshop-pack-finalization/promotion-map.json
```

For every original v0.1 semantic role and every proposed new distinct role, record:

```text
source: candidate | baseline_v0_1
status: CANDIDATE_REPLACES | BASELINE_RETAINS | KEEP_BOTH_DISTINCT | UNRESOLVED
proposed_id: <semantic ID>
reason: <short reason>
```

The proposal should clearly state:

- number of direct candidate replacements;
- number of baseline-retained roles;
- number of meaningful coexistence variants;
- unresolved count;
- preferred ingredient count.

No owner approval may be inferred.

---

## 9. Required visual evidence

Create:

```text
docs/reviews/visual/2026-08-21_workshop-pack-finalization/
```

Required files:

```text
01-final-inventory-a.png
02-final-inventory-b.png
03-distinct-variants.png
04-brush-paper-lamp-decisions.png
05-lamp-runtime-sizes.png
06-light-variants.png
07-final-baseline-composition.png
08-final-proposed-v02-composition.png
09-promotion-summary.png
PROMOTION.md
promotion-map.json
REVIEW.md
audit.json
```

### Evidence rules

- Inventory sheets together must show every proposed promoted finished asset with readable labels.
- `03-distinct-variants.png` must directly compare old/new shelf, blocks and pinboard-note variants and explain their distinct purpose without marketing language.
- `04-brush-paper-lamp-decisions.png` must show the exact final assets proposed for those roles.
- `05-lamp-runtime-sizes.png` must show both lamp variants at 192/128/96/64 px if both are proposed.
- `06-light-variants.png` must show light variants over the same room-value patch.
- Final composition must use the proposed v0.2 toolbox naturally; do not stuff every asset into one scene.
- No clipped review text.

---

## 10. REVIEW.md

Answer conservatively:

1. Which candidate assets directly replace v0.1?
2. Which v0.1 assets remain because they are still better for their role?
3. Which old/new pairs are kept together because they are meaningfully different objects?
4. How were brush bundle, paper stack and desk lamp resolved?
5. Which authoring ingredients are actually worth promoting?
6. Is any role unresolved?
7. Is the proposed Workshop v0.2 ready for owner promotion review?

Do not write `100% candidate` merely as a success metric. Toolbox usefulness is the metric.

---

## 11. No promotion/runtime changes in this gate

Do not create `assets/visual/environments/workshop/v0.2/` yet.

Do not alter runtime catalogues, Activities, scene renderer or Shell UI.

This gate prepares the owner promotion decision only.

After owner review, promotion will be a separate deterministic source-pack materialization step.

---

## 12. Owner attachment ZIP

Create at project root:

```text
./GREIA_VISUAL_REVIEW_WORKSHOP_PACK_FINALIZATION_2026-08-21.zip
```

Include the nine PNGs plus:

```text
PROMOTION.md
promotion-map.json
REVIEW.md
audit.json
```

Do not commit the ZIP itself.

Final response must include exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_WORKSHOP_PACK_FINALIZATION_2026-08-21.zip
```

---

## 13. Return

Commit and push only:

- bounded candidate corrections actually needed;
- promotion proposal;
- curated review evidence.

Return:

- exact commit SHA;
- direct replacement count;
- baseline-retained count;
- coexistence/new-role count;
- unresolved count;
- preferred ingredient count;
- review path;
- exact owner ZIP path.

Then stop Workshop work and wait for owner promotion review.

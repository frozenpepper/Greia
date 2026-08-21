# Clinic / Care Base Art Pack Reauthoring — Local Maintainer Agent Runbook

**Date:** 2026-08-21  
**Purpose:** reauthor the complete Clinic / Care base art pack at pack scale using the owner's local agent as a maintainer-side art-production tool.  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Parent plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`

## 1. Scope and intent

This is the next maintainer-side base-pack production task after Forest/Meadow and Workshop.

This task does **not** test arbitrary future user agents. Do not generalize your drawing technique into the model-agnostic visual-authoring skill.

Your question is only:

> can you produce a stronger complete Clinic / Care authoring toolbox than the current v0.1 baseline?

Work at pack scale. Do not spend the run perfecting one teddy bear, bed, cabinet, or stethoscope while the rest remains baseline quality.

## 2. Read first

Read:

```text
AGENTS.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
skills/greia-visual-authoring/SKILL.md
assets/visual/environments/clinic/v0.1/README.md
assets/visual/environments/clinic/v0.1/catalog.toml
```

Inspect all actual v0.1 source assets and any existing Clinic review/composition material before drawing.

## 3. Preserve provenance

Do not overwrite:

```text
assets/visual/environments/clinic/v0.1/
```

Create the candidate under:

```text
assets/visual/pack_candidates/clinic/2026-08-21/
```

## 4. Current baseline role inventory

The current catalogue contains 17 semantic roles:

```text
clinic.plush.bear
clinic.heart.fx
clinic.care.bowl
clinic.cabinet
clinic.room.floor.base
clinic.care.bed
clinic.heart.rug
clinic.care.kit
clinic.bandage.box
clinic.curtain.pair
clinic.side.table
clinic.room.wall.base
clinic.cushion
clinic.toy.stethoscope
clinic.bottle.set
clinic.care.window
clinic.window.light
```

Preserve or improve useful coverage for every role. If the candidate naturally produces a meaningfully different object from the baseline, preserve that possibility in metadata rather than forcing one-for-one replacement.

## 5. Art direction — child care, not hospital anxiety

The Clinic / Care pack should feel like a warm place where children care for toys/creatures/friends, not an intimidating medical ward.

Target:

- nurturing, calm, playful and reassuring;
- soft rounded forms without becoming featureless blobs;
- warm cream / mint / peach / gentle coral / sky accents as appropriate;
- tactile wood, cloth, ceramic, woven fabric and painted surfaces;
- clear material separation;
- soft daylight and believable grounding;
- enough detail to reward source-size inspection while remaining clean at runtime sizes.

Avoid:

- sterile cold hospital imagery;
- frightening or invasive medical imagery;
- needles, blood, wounds, surgical equipment, harsh red-cross visual dominance;
- generic plastic gradients applied to every object;
- flat programmer placeholders;
- tiny fiddly medical details that vanish at child-facing sizes.

The toy stethoscope/care-kit language should remain unmistakably friendly and pretend-care oriented.

## 6. Pack-scale quality target

Aim for a clearly stronger overall toolbox than v0.1:

- polished storybook / toy-diorama source art;
- strong silhouettes;
- richer material treatment;
- coherent lighting direction;
- convincing object contact/grounding;
- useful role variation;
- clean alpha;
- strong child-scale readability;
- no single repeated geometry/material formula infecting the entire pack.

The owner will judge actual pixels, not self-description.

## 7. Meaningful variation over replacement percentage

Use the Workshop lesson permanently:

> **The target is the strongest toolbox, not the highest replacement percentage.**

For each baseline role, the future promotion decision may be:

```text
CANDIDATE_REPLACES
BASELINE_RETAINS
KEEP_BOTH_DISTINCT
UNRESOLVED
```

Do not rename a genuinely different candidate object as though it were the same old object just to claim replacement.

Examples where distinct variants may be useful if they actually emerge:

- different care-bed/cushion arrangements;
- open vs closed care storage;
- different friendly window-light shapes;
- different care-kit configurations;
- different plush/comfort objects.

Do not manufacture variants artificially merely to increase asset count.

## 8. Authoring ingredients

You may create a **small curated** `ingredients/` set if useful for future Activity authors.

Potential examples:

- fabric patch/stitch detail;
- soft bandage-wrap motif;
- friendly heart/care accent;
- ceramic/glass bottle treatment;
- curtain fold/tie detail;
- gentle window-light source treatment.

Only propose ingredients that are genuinely reusable as authoring references/pieces. Keep experimental clutter out of the preferred list.

## 9. Runtime-size review

Test representative candidates across useful size tiers including 64 px where appropriate.

At small sizes preserve:

- silhouette;
- identity;
- primary value/color grouping;
- friendly/non-threatening read.

Thin tubing/details such as the toy stethoscope must not disappear into meaningless lines. If a detailed variant fails at small size, consider whether the baseline and candidate are meaningful scale-specific variants rather than forcing replacement.

## 10. Composition proof

Produce comparable 1024×600 Clinic/Care compositions using baseline and candidate toolboxes.

The candidate composition should demonstrate:

- wall/floor/base coherence;
- bed/cabinet/table/cushion grounding;
- a clear care/play focal area;
- warm window/light behavior;
- props that read as nurturing care tools rather than clinical instruments;
- no accidental floating or impossible furniture overlaps.

The composition is evidence of toolbox coherence, not a mandatory baked room.

## 11. Required review evidence

Create:

```text
docs/reviews/visual/2026-08-21_clinic-care-base-pack-reauthoring/
```

Required files:

```text
01-pack-overview-baseline.png
02-pack-overview-candidate.png
03-furniture-comfort-comparison.png
04-care-tools-props-comparison.png
05-room-light-background-comparison.png
06-runtime-sizes.png
07-baseline-composition.png
08-candidate-composition.png
09-detail-crops.png
REVIEW.md
audit.json
```

The baseline/candidate overviews must show **all 17 baseline roles** and all candidate finished assets proposed as their coverage/variants.

## 12. Comparison fairness

- comparable neutral backgrounds;
- comparable display scales;
- readable labels;
- no clipped review text;
- no marketing labels such as `MASTER`, `SUPERIOR`, `CLEARLY BETTER` on the producing agent's own sheets;
- compositions should have comparable room intent.

## 13. REVIEW.md

Answer conservatively:

1. Which candidate families are visibly stronger than baseline?
2. Which baseline assets remain stronger or more useful?
3. Did any candidate become a meaningfully distinct object that should coexist rather than replace?
4. Which assets are weakest at 64/128 px?
5. Does the pack remain friendly and care-oriented rather than clinical/scary?
6. Which proposed authoring ingredients are genuinely useful?
7. Is the pack ready for owner promotion review, and what remains uncertain?

Do not infer owner approval.

## 14. audit.json

Record:

- baseline directory;
- candidate directory;
- all 17 original semantic roles;
- candidate file(s) serving each role;
- any proposed distinct variant roles;
- proposed ingredients;
- source representation/dimensions where relevant;
- all review output paths;
- final pushed commit SHA.

## 15. Owner review ZIP

Create at project root:

```text
./GREIA_VISUAL_REVIEW_CLINIC_CARE_BASE_PACK_REAUTHORING_2026-08-21.zip
```

Include the nine PNGs, `REVIEW.md`, and `audit.json`.

Do not commit the ZIP itself. Commit candidate sources and underlying review evidence.

Final response must contain exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_CLINIC_CARE_BASE_PACK_REAUTHORING_2026-08-21.zip
```

## 16. Non-goals

Do not:

- modify Activities;
- modify the scene compositor;
- modify Shell UI;
- modify runtime catalogues merely to prove source art;
- create a generic Authoring Kit version;
- reopen Forest/Meadow or Workshop art refinement;
- claim your art process represents arbitrary user agents;
- run GitHub-hosted Actions.

## 17. Return

Commit and push:

- complete candidate pack sources;
- candidate metadata/catalogue;
- curated comparative evidence;
- review and audit.

Return:

- exact commit SHA;
- candidate path;
- candidate finished-asset count;
- any distinct variants added;
- proposed ingredient count;
- review path;
- exact ZIP path.

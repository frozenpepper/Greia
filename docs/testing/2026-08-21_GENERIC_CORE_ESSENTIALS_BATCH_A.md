# Greia Generic Visual Toolbox — Core Essentials Batch A

**Status:** EXECUTE  
**Date:** 2026-08-21  
**Authority:** `docs/reviews/visual/2026-08-21_generic-authoring-library-full-source-harvest/PRIMARY_REVIEW.md`  
**Taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Purpose

Create the next **generic**, cross-Activity source-art batch after the full source harvest.

This is not a themed room pack. Do not build a classroom, clinic, kitchen, fantasy village, or pond scene as the organizing concept.

The goal is to increase the authoring toolbox's cross-Activity leverage with a small set of broadly useful, visually strong, composable resources.

## 2. Core production principle

> **Generic assets encode reusable form; Activity-specific meaning/contents remain separable whenever practical.**

Do not reduce reusability by baking arbitrary contents into otherwise generic objects.

Examples:

- empty plate, not plate-with-toast as the only plate;
- empty bowl, not cereal permanently baked into the bowl;
- blank/open book with non-readable illustration shapes, not a specific story;
- blank dial/mechanical face plus useful components, not one narrowly themed machine;
- blank sign/board surfaces where text should be Activity/localization-owned.

This does not require everything to be decomposed into tiny runtime fragments. Source-level composability and semantic neutrality are the goal; runtime economy remains separate.

## 3. Preserve current library and provenance

Do not overwrite existing promoted/source pools.

Create a dedicated candidate source workspace, recommended:

`assets/visual/pack_candidates/generic_core_essentials/2026-08-21/`

This batch may reference existing preferred assets for style/material guidance, but should not duplicate their files unnecessarily.

Do not modify runtime PNG catalogues, Activities, scene compositor, or shared runtime manifests merely to prove this source-art batch.

## 4. Exact Batch A finished-asset scope

Create these **16 finished generic assets**.

### Interiors & Architecture — 3

1. `interior.door.timber.closed`
   - warm paneled timber interior door;
   - complete closed state;
   - child-readable hardware;
   - no signage/text.

2. `interior.door.timber.ajar`
   - same broad visual family but a genuinely useful ajar/open state;
   - convincing thickness/frame/perspective;
   - must not look like the closed SVG merely skewed.

3. `interior.opening.arch.simple`
   - open interior arch/room transition;
   - no baked themed decorations;
   - useful as a room-divider/opening element in many Activities.

### Furniture & Storage — 3

4. `furniture.seating.chair.spindle_wood`
   - standard four-leg wooden chair;
   - broadly useful for desk/dining/craft contexts;
   - stable silhouette at child-facing sizes.

5. `furniture.seating.armchair.soft_reading`
   - reauthor the weak reading-chair role;
   - soft upholstered chair with convincing volume/material;
   - neutral enough for bedroom/living/reading/calm-space scenes.

6. `furniture.storage.bookcase.tall_open`
   - reauthor the weak tall-bookcase role;
   - visually rich but not tied to a classroom;
   - books/objects may decorate it, but shelf structure must remain the reusable primary form.

### Reading / Paper / Decor — 4

7. `prop.book.open.picture_book`
   - reauthor weak open-storybook role;
   - no readable/baked language;
   - abstract child-friendly picture shapes are allowed;
   - strong page thickness/fold/material read.

8. `prop.books.stack.mixed`
   - reauthor weak book-stack role;
   - mixed cloth/paper covers;
   - no readable titles;
   - useful silhouette at 64–128 px.

9. `prop.decor.plant.potted_fern`
   - reauthor weak potted-plant role;
   - real botanical mass/leaf rhythm rather than a flat icon;
   - generic pot and interior use.

10. `prop.storage.basket.woven_empty`
   - reauthor weak basket role;
   - visibly woven material;
   - **empty generic basket** as the primary finished asset;
   - do not bake toys/food into it.

### Neutral Tableware — 3

11. `prop.tableware.plate.ceramic_empty`
   - glazed ceramic plate;
   - empty/neutral;
   - useful as base for Activity-local food or object composition.

12. `prop.tableware.bowl.ceramic_empty`
   - glazed ceramic bowl;
   - empty/neutral;
   - depth/readability must survive small sizes.

13. `prop.tableware.cup_saucer.ceramic`
   - generic cup + saucer set;
   - may visually imply a usable cup but must not bake a highly specific drink/story state;
   - no logo/text.

### Mechanical / Manipulative Components — 3

14. `component.mechanical.gear.wooden`
   - one broadly reusable wooden/toy-like gear;
   - strong tooth silhouette;
   - suitable as source component for authoring mechanisms.

15. `component.mechanical.gears.interlocking_pair`
   - two visibly interlocking gears;
   - useful finished manipulative as well as construction reference;
   - must not merely duplicate the single gear twice without composition consideration.

16. `component.mechanical.dial_hands.blank`
   - generic circular dial/clock-like face with movable-looking hands/pointers;
   - **no baked numerals or text**;
   - can support clocks, gauges, puzzles, machines, timers or teaching activities after adaptation.

## 5. Optional authoring ingredients — maximum 4

Only create an ingredient when it has clear cross-asset authoring leverage. Maximum four.

Good candidates might include:

- timber door hardware/hinge-handle detail;
- woven wicker strip/corner treatment;
- ceramic rim/highlight treatment;
- generic mechanical axle/pivot/hand set.

Do not create fragments merely to hit a count.

Ingredients are source-authoring resources, not automatically runtime assets.

## 6. Visual quality expectations

Use the strongest current Greia source art as style reference, especially promoted Forest/Meadow v0.3 and Workshop v0.2.

Target:

- polished storybook / toy-diorama quality;
- warm but material-specific color/value treatment;
- convincing wood, fabric, paper, ceramic, foliage, wicker and mechanical materials;
- readable silhouette before micro-detail;
- clean alpha;
- grounded objects where appropriate;
- no generic plastic gradient applied to every material;
- no enlarged-vector-icon look at 256–512 px;
- no baked language;
- no unnecessary themed ornament that reduces reuse.

## 7. Cross-category coherence test

This batch deliberately spans unrelated object families.

The batch succeeds only if all 16 feel Greia-coherent **without looking like one themed room set**.

Prepare neutral compositions demonstrating at least:

- a small interior vignette using door/arch/chair/bookcase;
- a tabletop/reading vignette using books, plant, basket and tableware;
- a small maker/manipulative vignette using the mechanical components.

These compositions are review evidence only. Do not turn them into new themed packs.

## 8. Target-size review

Render representative assets at:

- 512 px;
- 256 px;
- 128 px;
- 64 px.

At minimum include:

- chair;
- open book;
- basket;
- plate/bowl/cup;
- gear;
- dial.

Do not claim that fine source detail survives if the rendered evidence does not show it.

## 9. Candidate metadata

Create a candidate catalogue/manifest with generic semantic IDs, source paths, family/role, alpha behavior, recommended size range, and candidate admission state.

Do not mark new resources `preferred` before owner pixel review.

Use:

`library_status = "candidate_reference"`

until owner review explicitly promotes them.

## 10. Required evidence

Create curated evidence under:

`docs/reviews/visual/2026-08-21_generic-core-essentials-batch-a/`

Required PNGs:

1. `01-full-candidate-inventory.png` — all 16 finished assets + any ingredients.
2. `02-architecture-furniture.png` — doors/opening/chair/armchair/bookcase at useful review size.
3. `03-books-plant-basket.png` — books/plant/basket detail comparison against weak source roles where applicable.
4. `04-neutral-tableware.png` — empty plate, empty bowl, cup/saucer; clearly show neutrality/composability.
5. `05-mechanical-components.png` — single gear, pair, blank dial/hands; no baked labels/numerals.
6. `06-runtime-sizes.png` — representative 512/256/128/64 proof.
7. `07-interior-vignette.png` — neutral architecture/furniture composition.
8. `08-tabletop-reading-vignette.png` — neutral cross-family composition.
9. `09-maker-vignette.png` — neutral mechanical composition.
10. `10-detail-crops.png` — material proof at source scale.

Also include:

- `REVIEW.md` with conservative self-assessment;
- `audit.json` with exact asset count and file mapping.

Follow `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`.

## 11. Owner transfer ZIP

Create at project root, do not commit:

`GREIA_VISUAL_REVIEW_GENERIC_CORE_ESSENTIALS_BATCH_A_2026-08-21.zip`

Include only the curated review PNGs plus `REVIEW.md` and `audit.json`.

## 12. Stop conditions

Stop and report instead of improvising if:

- the expected generic library/source paths are missing;
- the source pack references are broken;
- you would need to modify runtime architecture to complete source art;
- output cannot be rendered for evidence;
- a requested asset cannot be made semantically neutral without changing its role.

## 13. Prohibited drift

Do not:

- create a kitchen/dining themed pack;
- create a classroom themed pack;
- build a complete scene/application;
- rework Forest/Meadow or Workshop assets not required by this batch;
- reopen Clinic finalization;
- produce food assets merely because tableware exists;
- bake toast/cereal/tea/text/numerals into the generic base resource as its only form;
- generate dozens of near-variants;
- change runtime consumer code;
- claim owner acceptance.

## 14. Return

Commit and push the candidate source workspace, catalogue, and curated evidence.

Return:

- pushed commit SHA;
- exact candidate path;
- 16 finished-asset list;
- any ingredient list;
- evidence path;
- project-root owner ZIP path;
- concise conservative self-assessment.

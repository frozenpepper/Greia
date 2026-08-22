# Primary Review — Generic Core Essentials Batch A

**Date:** 2026-08-22  
**Candidate commit reviewed:** `574f19530ee292a81225ff14c09ad8b35f6cf933`  
**Candidate source:** `assets/visual/pack_candidates/generic_core_essentials/2026-08-21/`  
**Evidence reviewed:** actual owner-transfer PNGs from `GREIA_VISUAL_REVIEW_GENERIC_CORE_ESSENTIALS_BATCH_A_2026-08-21.zip`

## 1. Verdict

Batch A is **useful and successful as a generic-toolbox tranche**, but the producing agent's self-assessment overstates the craft quality of several assets.

Do **not** run another broad redraw/finalization loop on this batch. The generic authoring library explicitly supports both `preferred` resources and weaker `candidate_reference` resources. Use that distinction instead of polishing every item until it is perfect.

The batch proves the intended generic-library direction:

- objects are organized by reusable semantic need rather than a themed room;
- tableware is empty/neutral rather than carrying baked food;
- mechanical pieces avoid baked labels/numerals;
- unrelated asset families can coexist in neutral compositions;
- source-level generic forms can support later Activity-specific composition.

The next step is **selective admission plus making this library easy for arbitrary Activity-authoring agents to discover and use**, not another art-production batch.

## 2. Owner dispositions

### 2.1 Admit as `preferred`

These finished resources are strong/useful enough for direct consideration by Activity authors:

1. `interior.door.timber.closed`
2. `interior.opening.arch.simple`
3. `furniture.seating.chair.spindle_wood`
4. `furniture.storage.bookcase.tall_open`
5. `prop.storage.basket.woven_empty`
6. `prop.tableware.bowl.ceramic_empty`
7. `prop.tableware.cup_saucer.ceramic`
8. `component.mechanical.gears.interlocking_pair`
9. `component.mechanical.dial_hands.blank`

Preferred authoring ingredients:

10. `ingredient.hardware.door_hinge_handle`
11. `ingredient.mechanical.axle_hands`

`preferred` here means **good generic direct-use/toolbox material**, not immutable gold-standard art.

### 2.2 Keep as `candidate_reference`

These are useful references or adaptation bases but should not be presented as first-choice direct-reuse art:

1. `interior.door.timber.ajar`
   - the door perspective itself is useful;
   - the built-in pale room/jamb reveal makes the source less composition-neutral than the closed door and arch;
   - in the neutral vignette it reads somewhat like a freestanding pasted portal instead of a naturally integrated wall opening.

2. `furniture.seating.armchair.soft_reading`
   - substantially better than the legacy placeholder;
   - still reads as an enlarged vector/icon object: semicircular back, very smooth green gradients, circular scroll-arm ends;
   - material language is not convincing enough for preferred direct reuse.

3. `prop.book.open.picture_book`
   - semantically neutral and readable;
   - still visually simple/icon-like with limited paper/page material depth;
   - useful for COMPOSE/ADAPT and as a source reference.

4. `prop.books.stack.mixed`
   - useful silhouette and no baked language;
   - still comparatively flat/outlined and less materially convincing than stronger preferred assets.

5. `prop.decor.plant.potted_fern`
   - the current image does not convincingly read as a lush parlor fern; it resembles a sparse spiky houseplant;
   - keep the role/reference, but do not claim this closes the botanical quality gap.

6. `prop.tableware.plate.ceramic_empty`
   - semantic neutrality is correct;
   - pale value/edge treatment becomes very weak at small size and the plate nearly disappears in the supplied 64px row;
   - keep as a reference/adaptation base rather than preferred direct reuse.

7. `component.mechanical.gear.wooden`
   - useful mechanical silhouette;
   - material/read is not convincingly wooden because the grey outer structure and glossy orange center make it read more like a mixed metal/toy component;
   - useful reference, but the semantic/material label should not overclaim birch/wood realism.

## 3. Evidence observations

### Architecture / furniture

The closed door, arch and spindle chair are clean, readable and broadly reusable. The bookcase remains fairly simple but is materially and structurally adequate for toolbox use.

The ajar-door state is useful but its integrated room reveal reduces composability. The armchair is the weakest large furniture asset in the tranche and should remain a candidate reference.

### Reading / storage

The basket is the strongest of the reauthored Reading/Classroom-derived roles: it is visibly empty, has clear depth and weave, and is broadly reusable.

The new books are improvements over v0.1 but still look like simple vector illustrations at source review size. They are useful reference/adaptation material rather than preferred finished art.

The plant does not visually support the producing agent's description of a "lush parlor fern" and remains a quality gap.

### Tableware

The composability correction is successful: plate, bowl and cup/saucer contain no baked food/liquid/story state. This is the right generic-authoring pattern.

The bowl and cup/saucer have enough volume and contrast for preferred toolbox use. The plate is too pale/thin at small scale and remains candidate reference.

### Mechanical components

The interlocking pair and blank radial dial are strong generic building material. The dial is text/numeral-free and can be adapted into several mechanisms.

The single gear is visually usable but the claimed wooden material is not convincing enough to make it a preferred wooden reference.

## 4. Runtime-size evidence correction

The supplied scale sheet does **not** justify every `min_recommended_px` claim in `catalog.toml`.

It visibly demonstrates representative rows, but not every asset/size combination. In particular, metadata must not imply a 32px or 48px quality guarantee merely because the catalogue contains that number.

During admission:

- preserve only size claims supported by actual review/evidence or conservatively raise the minimum;
- do not add new art merely to prove arbitrary lower bounds;
- `candidate_reference` assets may keep conservative ranges suitable for authoring/reference use.

## 5. No Batch A redraw loop

Do not execute a Batch A "finalization" that redraws the seven candidate-reference assets one-by-one.

Their state is useful information:

- some resources are ready for direct reuse;
- some are useful adaptation/reference material;
- some identify real future quality gaps.

That distinction is exactly why the generic library has admission states.

## 6. Next architectural milestone

Greia now has enough generic breadth that the next highest-value work is **authoring discovery/tooling**, not another 12–18 asset batch.

An arbitrary Activity-authoring agent should not need to manually grep six TOMLs or know historical source directories. Provide a small deterministic authoring-time discovery helper over the existing semantic indexes and teach the visual-authoring skill to use it.

Next runbook:

`docs/testing/2026-08-22_GENERIC_VISUAL_LIBRARY_ADMISSION_AND_DISCOVERY_TOOLING.md`

That gate must:

1. selectively admit Batch A according to this review;
2. keep the 7 weaker resources as `candidate_reference` rather than redrawing them;
3. add a simple authoring-time query/list/show tool over the generic semantic indexes;
4. update `skills/greia-visual-authoring/SKILL.md` to use the discovery helper when available;
5. preserve the runtime boundary — this is authoring tooling, not a new runtime catalogue/cache.

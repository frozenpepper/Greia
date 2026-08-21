# Primary Review — Generic Authoring Library Consolidation

**Date:** 2026-08-21  
**Status:** STRUCTURE ACCEPTED / COVERAGE CONCLUSION REJECTED AS PREMATURE

## 1. What is accepted

The architectural direction is correct:

- generic semantic collections are the primary Activity-authoring discovery layer;
- source/theme bundles remain provenance/source pools;
- source files are referenced rather than duplicated;
- Clinic/Care was correctly treated as a source pool rather than automatically promoted as a core generic pack;
- specialized medical assets were kept out of the primary generic core.

The first six generic collection files under `assets/visual/authoring_library/` are a useful structural foundation.

## 2. Critical problem

The reported coverage gaps are **not yet authoritative** because the consolidation only harvested:

- Forest / Meadow v0.3;
- Workshop v0.2;
- Clinic / Care 2026-08-21 candidate.

Greia already contains additional source pools that were not harvested before the gap analysis was produced:

- `assets/visual/environments/reading_classroom/v0.1/`;
- `assets/visual/environments/fantasy_village_night/v0.1/`;
- `assets/visual/environments/water_pond/v0.1/`.

That omission materially changes the conclusions.

## 3. Concrete examples proving the current gap report is incomplete

The Reading/Classroom source pool already contains:

- `reading.book.stack`;
- `reading.open.storybook`;
- `reading.reading.chair`;
- `reading.beanbag`;
- `reading.potted.plant`;
- `reading.toy.basket`;
- `reading.tall.bookcase`;
- `reading.floor.cushion`;
- `reading.chalkboard`.

Therefore claims such as:

- “books are missing”;
- “reading chair is missing”;
- “indoor potted plants are missing”;

cannot be treated as true inventory gaps until those existing assets have been reviewed and classified.

The Fantasy/Village/Night source pool already contains potentially reusable objects such as:

- stone bridge;
- lantern post;
- wooden signpost;
- stone well;
- cobblestone edge;

alongside clearly more specialized fantasy/village assets.

The Water/Pond source pool already contains potentially reusable nature/water objects such as:

- water base;
- pond bank edge;
- lily-pad cluster;
- reeds;
- water lilies;
- small dock;
- stepping stones;
- ripple ring;
- shimmer/reflection overlays;
- dragonfly/bubble/fish-shadow FX.

These must be harvested before any new generic water/nature batch is justified.

## 4. Important distinction: missing vs present-but-not-good-enough

The next audit must separate:

```text
PREFERRED_GENERIC
CANDIDATE_GENERIC
REAUTHOR_GENERIC
SPECIALIZED_THEME_ONLY
DUPLICATE_OR_SUPERSEDED
UNRESOLVED
```

This matters because an existing `open_storybook.svg` means “storybook” is not an inventory gap. It may still be a **quality gap** if the existing source is too weak to become a preferred Greia authoring reference.

Do not create new artwork merely because the current generic index omitted an existing source asset.

## 5. Generic-library status must be explicit

The current authoring-library README calls the library canonical while it references a mixture of:

- promoted source assets;
- owner-reviewed candidate source assets.

Future indexes must make quality/admission state explicit enough that arbitrary Activity-authoring agents can distinguish:

- preferred reviewed asset;
- candidate/reference asset;
- specialized source-only asset.

The primary discovery layer should prefer reviewed/promoted assets without hiding useful candidate references that may still help COMPOSE/ADAPT work.

## 6. Current “71 reusable visual assets” claim

Keep finished assets and authoring ingredients conceptually separate.

The first consolidation has:

```text
66 indexed finished assets
5 indexed authoring ingredients
```

It is fine to say “71 indexed resources” if clearly stated, but do not imply that ingredients and finished assets are interchangeable runtime-ready visuals.

## 7. Decision on the proposed 16-asset batch

**DO NOT START IT YET.**

The proposed `Generic Living & Learning Essentials` batch is based on an incomplete source inventory and would duplicate assets that already exist in Reading/Classroom.

No new generic art-production batch is authorized until the remaining source pools have been harvested and the coverage report recomputed.

## 8. Exact next action

Execute:

`docs/testing/2026-08-21_GENERIC_VISUAL_LIBRARY_FULL_SOURCE_HARVEST.md`

That gate must:

1. inspect all remaining existing source pools before drawing anything new;
2. classify generic usefulness and quality/admission state;
3. update the generic semantic indexes without duplicating source files;
4. produce a visual review package for currently unreviewed generic candidates;
5. recompute gaps as **true missing roles** versus **present-but-needing-reauthoring roles**;
6. only then recommend the next generic art-production batch.

## 9. Workstream rule

The goal is not to maximize the number of new drawings.

The goal is to build the strongest, most discoverable generic visual toolbox from everything Greia already owns, then create only the genuinely missing or inadequate high-value resources.